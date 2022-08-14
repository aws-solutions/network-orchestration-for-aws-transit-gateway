# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

from os import environ
import inspect
from time import sleep
from datetime import datetime, timedelta
from state_machine.lib.organizations import Organizations
import json
from secrets import choice
from state_machine.utils.metrics import Metrics
from state_machine.lib.ec2 import EC2
from state_machine.lib.dynamodb import DDB
from state_machine.lib.ram import RAM
from state_machine.lib.sts import STS
from state_machine.lib.sns import SNS
import logging
from state_machine.lib.cloud_watch_logs import CloudWatchLogs
from state_machine.utils.helper import timestamp_message, current_time
from state_machine.utils.string_manipulation import convert_string_to_list
from state_machine.lib.assume_role_helper import AssumeRole
from state_machine.lib.exceptions import (
    ResourceNotFoundException,
    AttachmentCreationInProgressException,
    AlreadyConfiguredException,
    ResourceBusyException,
    RouteTableNotFoundException,
)

CLASS_EVENT = " Class Event"
EXECUTING = "Executing: "
TGW_VPC_ERROR = "The TGW-VPC Attachment is not in 'available'"


class TransitGateway:
    """
    This class contains functions to manage Transit Gateway related resources.
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = self.event.get("region")
        self.assume_role = AssumeRole()
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)

    def _session(self, account_id):
        # instantiate EC2 sessions
        return EC2(
            credentials=self.assume_role(account_id),
        )

    def _print(self, description, response):
        self.logger.info(f"Printing {description}")
        self.logger.info(response)

    def _message(self, method, e):
        return {
            "FILE": __file__.split("/")[-1],
            "CLASS": self.__class__.__name__,
            "METHOD": method,
            "EXCEPTION": str(e),
        }

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)
            ec2.create_tags(
                resource, "STNOStatus-" + key, timestamp_message(message)
            )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def get_transit_gateway_vpc_attachment_state(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            # skip checking the TGW attachment status if it does not exist
            if self.event.get("TgwAttachmentExist").lower() == "yes":
                ec2 = self._session(self.spoke_account_id)
                response = ec2.get_transit_gateway_vpc_attachment_state(
                    self.event.get("TransitGatewayAttachmentId")
                )
                self._print("Transit Gateway Attachment State: ", response)
                # the list should always contain a single item
                self.event.update({"AttachmentState": response[0].get("State")})
                if (
                    response[0].get("State") == "pending"
                    or response[0].get("State") == "modifying"
                ):
                    # if the tgw attachment stage is modifying and multiple state machine executions are in progress
                    # sleeping for random number of seconds to avoid race condition failure.
                    _seconds = choice(range(5, 10))
                    sleep(_seconds)
            else:
                # set attachment state to deleted because it does not exist
                # and creation was skipped in the CRUD operation stage.
                # The attachment was previously deleted or was never created.
                self.logger.info("TGW Attachment does not exist.")
                self.event.update({"AttachmentState": "deleted"})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def describe_transit_gateway_vpc_attachments(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)
            states = ["available", "pending", "modifying"]
            response = ec2.describe_transit_gateway_vpc_attachments(
                environ.get("TGW_ID"), self.event.get("VpcId"), states
            )
            self._print("Transit Gateway Attachment List", response)

            if response:
                self.event.update({"TgwAttachmentExist": "yes"})

                # check if the subnet is already in the TGW VPC Attachment
                for attachment in response:
                    if attachment.get("VpcId") == self.event.get("VpcId"):
                        # add TGW Attachment Id in the event for modifications in the state machine
                        self.event.update(
                            {
                                "TransitGatewayAttachmentId": attachment.get(
                                    "TransitGatewayAttachmentId"
                                )
                            }
                        )
                        self.event.update(
                            {"AttachmentState": attachment.get("State")}
                        )
                        # look for subnet id in existing attachment
                        if self.event.get("SubnetId") in attachment.get(
                            "SubnetIds"
                        ):
                            self._print(
                                "subnet found in existing attachment",
                                self.event.get("SubnetId"),
                            )
                            self.event.update(
                                {"FoundExistingSubnetInAttachment": "yes"}
                            )
                        else:
                            self._print(
                                "subnet list for existing TGW-VPC attachment",
                                attachment.get("SubnetIds"),
                            )
                            self.event.update(
                                {"FoundExistingSubnetInAttachment": "no"}
                            )
            else:
                self.event.update({"TgwAttachmentExist": "no"})
                self.event.update({"AttachmentState": "does-not-exist"})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _create_tgw_attachment(self, ec2):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            self.logger.info(
                "Creating TGW Attachment with Subnet ID: {}".format(
                    self.event.get("SubnetId")
                )
            )
            response = ec2.create_transit_gateway_vpc_attachment(
                environ.get("TGW_ID"),
                self.event.get("VpcId"),
                self.event.get("SubnetId"),
            )
            self._print("Create Transit Gateway Attachment Response", response)
            self.event.update(
                {
                    "AttachmentState": response.get(
                        "TransitGatewayVpcAttachment", {}
                    ).get("State")
                }
            )
            self.event.update(
                {
                    "TransitGatewayAttachmentId": response.get(
                        "TransitGatewayVpcAttachment", {}
                    ).get("TransitGatewayAttachmentId")
                }
            )
            self.event.update({"Action": "CreateTgwVpcAttachment"})
            self.event.update({"TgwAttachmentExist": "yes"})
        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""

            # If there is another step function execution happening in parallel that is creating
            # an attachment, we'd get a DuplicateTransitGatewayAttachment error (code ResourceNotFoundException).
            # Raise a specific exception so that the step function can try again:
            if error_code == "DuplicateTransitGatewayAttachment":
                raise AttachmentCreationInProgressException(e)

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _delete_tgw_attachment(self, ec2):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            # if this exception is thrown then it is safe to delete transit gateway attachment
            delete_response = ec2.delete_transit_gateway_vpc_attachment(
                self.event.get("TransitGatewayAttachmentId")
            )
            self._print(
                "Delete Transit Gateway Attachment Response", delete_response
            )
            self.event.update(
                {
                    "AttachmentState": delete_response.get(
                        "TransitGatewayVpcAttachment", {}
                    ).get("State")
                }
            )
            # during this step the associations and propagation are also removed.
            self._create_tag(
                self.event.get("VpcId"),
                "VPCAttachment",
                "VPC has been detached from the Transit Gateway",
            )
            self._create_tag(
                self.event.get("VpcId"),
                "VPCAssociation",
                "VPC has been dissociated with the Transit Gateway Routing Table/Domain",
            )
            self._create_tag(
                self.event.get("VpcId"),
                "VPCPropagation",
                "VPC RT propagation has been disabled from the "
                "Transit Gateway Routing Table/Domain",
            )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _add_subnet_to_tgw_attachment(self, ec2):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            self.logger.info(
                "Add Subnet: {} to Tgw Attachment".format(
                    self.event.get("SubnetId")
                )
            )
            self.event.update({"Action": "AddSubnet"})
            response = ec2.add_subnet_to_tgw_attachment(
                self.event.get("TransitGatewayAttachmentId"),
                self.event.get("SubnetId"),
            )
            if response.get("Error") == "IncorrectState":
                raise ResourceBusyException
            elif response.get("Error") == "DuplicateSubnetsInSameZone":
                self.event.update({"Status": "auto-rejected"})
                comment = "DuplicateSubnetsInSameZoneError: In a TGW VPC attchment, you can add only one subnet per Availability Zone."
                self.event.update({"Comment": comment})
                self._create_tag(self.event.get("SubnetId"), "Subnet", comment)
            else:
                self._print(
                    "Modify (Add Subnet) Transit Gateway Attachment Response",
                    response,
                )
                self.event.update(
                    {
                        "AttachmentState": response.get(
                            "TransitGatewayVpcAttachment", {}
                        ).get("State")
                    }
                )
                self._create_tag(
                    self.event.get("SubnetId"),
                    "Subnet",
                    "Subnet appended to the TGW attachment.",
                )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _remove_subnet_from_tgw_attachment(self, ec2):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            self.logger.info(
                "Remove Subnet: {} from Tgw Attachment".format(
                    self.event.get("SubnetId")
                )
            )
            self.event.update({"Action": "RemoveSubnet"})
            response = ec2.remove_subnet_from_tgw_attachment(
                self.event.get("TransitGatewayAttachmentId"),
                self.event.get("SubnetId"),
            )
            if response.get("Error") == "IncorrectState":
                raise ResourceBusyException
            # this exception is caught if the last subnet in the attachment is being deleted
            elif response.get("Error") == "InsufficientSubnetsException":
                self.logger.info(
                    "Insufficient Subnets when calling the ModifyTransitGatewayVpcAttachment operation, "
                    "This is the last subnet in the TGW-VPC Attachment. Deleting TGW Attachment..."
                )
                self.event.update({"Action": "DeleteTgwVpcAttachment"})
                self._delete_tgw_attachment(ec2)
            else:
                self._print(
                    "Modify (Remove Subnet) Transit Gateway Attachment Response",
                    response,
                )
                self.event.update(
                    {
                        "AttachmentState": response.get(
                            "TransitGatewayVpcAttachment", {}
                        ).get("State")
                    }
                )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def tgw_attachment_crud_operations(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)

            # create attachment if TGW Attachment does not exist and Subnet tag exists
            if (
                self.event.get("TgwAttachmentExist") == "no"
                and self.event.get("SubnetTagFound") == "yes"
            ):
                self._create_tgw_attachment(ec2)
                self._create_tag(
                    self.event.get("SubnetId"),
                    "Subnet",
                    "Subnet added to the TGW attachment.",
                )
                self._create_tag(
                    self.event.get("VpcId"),
                    "VPCAttachment",
                    "VPC has been attached to the Transit Gateway",
                )

            # update - add subnet to attachment
            if (
                self.event.get("FoundExistingSubnetInAttachment") == "no"
                and self.event.get("SubnetTagFound") == "yes"
            ):
                self._add_subnet_to_tgw_attachment(ec2)

            # update - remove subnet from attachment
            # OR
            # delete - if only one subnet left in attachment
            elif (
                self.event.get("FoundExistingSubnetInAttachment") == "yes"
                and self.event.get("SubnetTagFound") == "no"
            ):
                self._remove_subnet_from_tgw_attachment(ec2)
                self._create_tag(
                    self.event.get("SubnetId"),
                    "Subnet",
                    "Subnet removed from the TGW attachment.",
                )
            else:
                self.logger.info("No action performed.")

            # find existing TGW route table association to support update action
            self._find_existing_tgw_rt_association(
                ec2, self.event.get("RouteTableList")
            )

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _extract_tgw_route_table_names(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            # look for defined tag keys in the event
            associate_with, propagate_to = None, None
            for key, value in self.event.items():
                if (
                    key.lower().strip()
                    == environ.get("ASSOCIATION_TAG").lower().strip()
                ):
                    self.logger.info(
                        "Key matched {}:".format(
                            environ.get("ASSOCIATION_TAG").lower().strip()
                        )
                    )
                    self.logger.info("{} : {}".format(key, value))
                    associate_with = value.lower().strip()
                elif (
                    key.lower().strip()
                    == environ.get("PROPAGATION_TAG").lower().strip()
                ):
                    self.logger.info(
                        "Key matched {}:".format(
                            environ.get("PROPAGATION_TAG").lower().strip()
                        )
                    )
                    self.logger.info("{} : {}".format(key, value))
                    propagate_to = [x.lower().strip() for x in value]
            return associate_with, propagate_to
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def describe_transit_gateway_route_tables(self):
        try:

            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = EC2()
            # describe tgw route tables for the provided TGW ID
            response = ec2.describe_transit_gateway_route_tables(
                environ.get("TGW_ID")
            )
            self._print("Transit Gateway Route Tables", response)

            # returns a tuple (string, list)
            (
                associate_with_table,
                propagate_to_tables,
            ) = self._extract_tgw_route_table_names()
            self.logger.info(
                "Table Names in the association: {} | propagation: {}".format(
                    associate_with_table, propagate_to_tables
                )
            )

            # extract route table ids
            rtb_list = self._extract_route_table_ids(
                associate_with_table, propagate_to_tables, response
            )
            self.event.update({"RouteTableList": rtb_list})

            # find existing TGW route table association to support update action
            # needed for 'Association changed?' choice
            self._find_existing_tgw_rt_association(
                ec2, self.event.get("RouteTableList")
            )

            # find existing TGW route table propagations
            self.get_transit_gateway_attachment_propagations()

            # set approval flag
            self._set_approval_flag(response)

            # set status based on the approval workflow
            self._set_status()

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _process_conditional_approval_rule(
        self, rule, route_type="Association"
    ):
        """
        Takes a rule object, and returns 'accept|reject|approvalrequired'.

        Input:
            rule: Dict object that looks like:
                default_association: approvalrequired | accept | reject
                default_propagation: approvalrequired | accept | reject
                1 ->
                    InOUs: list of OU paths
                    NotInOUs: list of OU paths
                    Association: approvalrequired | accept | reject
                    Propagation: approvalrequired | accept | reject
                2 -> ...
            route_type: Association|Propagation

        Returns: "accept|reject|approvalrequired" based on OU membership.
        """

        # Default action if nothing matches:
        default_action = "approvalrequired"
        action = rule.get(f"default_{route_type}", default_action)

        # Get current event account's OU:
        ou_path = self.event.get("AccountOuPath")

        if not ou_path:
            self.logger.info("Cannot get account OU path from event.")
            return action

        # Do a case insensitive match:
        ou_path = ou_path.lower()

        # Go through each number:
        for rule_id in sorted([x for x in rule.keys() if type(x) == int]):
            should_be_in = True
            if "InOUs" in rule[rule_id]:
                should_be_in = True
                ou_list = rule[rule_id]["InOUs"]
            elif "NotInOUs" in rule[rule_id]:
                should_be_in = False
                ou_list = rule[rule_id]["NotInOUs"]

            # Go through each OU in the list:
            for match_ou in ou_list:
                # Add / around the OU path if it's not there already:
                if not match_ou.startswith("/"):
                    match_ou = f"/{match_ou}"
                if not match_ou.endswith("/"):
                    match_ou = f"{match_ou}/"

                if should_be_in and ou_path.startswith(match_ou):
                    return rule[rule_id].get(route_type, default_action)
                if not should_be_in and not ou_path.startswith(match_ou):
                    return rule[rule_id].get(route_type, default_action)

        return action

    def _set_approval_flag(self, response):
        # response is the output of ec2.describe_transit_gateway_route_tables()
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            # set approval required to 'No', assuming if tag is not present it does not require approval
            self.event.update({"ApprovalRequired": "no"})
            association_route_table = self.event.get("AssociationRouteTableId")
            if not association_route_table or association_route_table == "none":
                # No association tag, propagations are irrelevant. Skip:
                return
            propagation_route_tables = self.event.get(
                "PropagationRouteTableIds", []
            )
            # The following is a dict of:
            #   route-table-id:
            #     conditional_approval: True|False,
            #     association_approval: True|False
            #     propagation_approval: True|False,
            #     rule: {} # rule object
            route_table_approval_required = {}

            # Go through each route table:
            for table in response:
                route_table_id = table.get("TransitGatewayRouteTableId")
                if (
                    route_table_id == association_route_table
                    or route_table_id in propagation_route_tables
                ):
                    # Collect ApprovalRule-* tag keys and values if any:
                    route_table_rule_tags = {}
                    route_table_approval_required[route_table_id] = {
                        "association_approval": False,
                        "propagation_approval": False,
                    }
                    # iterate through tags for each route table
                    for tag in table.get("Tags"):
                        approval_key = environ.get("APPROVAL_KEY")
                        tag_key = tag.get("Key").lower().strip()
                        tag_value = tag.get("Value").lower().strip()
                        if tag_key == approval_key.lower().strip():
                            self.logger.info(
                                "Found approval tag key set to '{}')".format(
                                    tag_value
                                )
                            )
                            if tag_value == "yes":
                                # if approval required for this route table change
                                self.logger.info(
                                    "Any change to this route domain require approval."
                                )
                                route_table_approval_required[
                                    route_table_id
                                ] = {
                                    "association_approval": True,
                                    "propagation_approval": True,
                                }
                            elif tag_value == "conditional":
                                route_table_approval_required[
                                    route_table_id
                                ] = {
                                    "conditional_approval": True,
                                }
                        elif tag_key.startswith("approvalrule"):
                            # Collect the rules for this route table:
                            route_table_rule_tags[tag_key] = tag_value

                    # If the approval is conditional, construct the rule object to insert into route_table_approval_required:
                    if route_table_approval_required.get(
                        route_table_id, {}
                    ).get("conditional_approval"):
                        # Convert rule tags into a rule object
                        rule = {}
                        rule["default_association"] = rule[
                            "default_propagation"
                        ] = "approvalrequired"
                        if (
                            "approvalrule-default-association"
                            in route_table_rule_tags
                        ):
                            rule["default_association"] = route_table_rule_tags[
                                "approvalrule-default-association"
                            ]
                        if (
                            "approvalrule-default-propagation"
                            in route_table_rule_tags
                        ):
                            rule["default_propagation"] = route_table_rule_tags[
                                "approvalrule-default-propagation"
                            ]
                        # Get all the Approval-NN-* tags in a group, from 00 to 99 if it exists:
                        for i in range(1, 100):
                            zero_padded_number = str(i).zfill(2)
                            # Get all rules, if any, that starts with this number:
                            rule_group_tags = {
                                k: v
                                for k, v in route_table_rule_tags.items()
                                if k.startswith(
                                    f"approvalrule-{zero_padded_number}-"
                                )
                            }
                            if len(rule_group_tags) == 0:
                                # Nothing here, don't check any more numbers:
                                break
                            # Create rule block for the number i
                            rule_number_block = {}

                            def csv_to_list(csv):
                                return [
                                    x.strip()
                                    for x in filter(None, csv.split(","))
                                ]

                            check_tag = (
                                f"approvalrule-{zero_padded_number}-inous"
                            )
                            if rule_group_tags.get(check_tag):
                                ou_list = csv_to_list(
                                    rule_group_tags.get(check_tag)
                                )
                                rule_number_block["InOUs"] = ou_list
                            check_tag = (
                                f"approvalrule-{zero_padded_number}-notinous"
                            )
                            if rule_group_tags.get(check_tag):
                                ou_list = csv_to_list(
                                    rule_group_tags.get(check_tag)
                                )
                                rule_number_block["NotInOUs"] = ou_list
                            check_tag = (
                                f"approvalrule-{zero_padded_number}-association"
                            )
                            if rule_group_tags.get(check_tag):
                                rule_number_block[
                                    "Association"
                                ] = rule_group_tags.get(check_tag)
                            check_tag = (
                                f"approvalrule-{zero_padded_number}-propagation"
                            )
                            if rule_group_tags.get(check_tag):
                                rule_number_block[
                                    "Propagation"
                                ] = rule_group_tags.get(check_tag)
                            # Set the rule number:
                            rule[i] = rule_number_block

                        # Insert final rule object for this route table ID:
                        route_table_approval_required[route_table_id][
                            "rule"
                        ] = rule

            # If the approvalrequired is conditional, we need to process the rules and then
            # for the route_table_approval_required dictonary,
            # set the tgw-rtb-id -> association_approval|propagation_approval to True/False
            # for the next section:
            if route_table_approval_required[association_route_table].get(
                "conditional_approval"
            ):
                rule = route_table_approval_required[
                    association_route_table
                ].get("rule")
                if rule:
                    # action will be one of "accept|reject|approvalrequired"
                    action = self._process_conditional_approval_rule(
                        rule, route_type="Association"
                    )
                    self.logger.info(
                        f'Conditional rule result is "{action}" for association route table {association_route_table}'
                    )
                    if action == "accept":
                        route_table_approval_required[association_route_table][
                            "association_approval"
                        ] = False
                    elif action == "approvalrequired":
                        route_table_approval_required[association_route_table][
                            "association_approval"
                        ] = True
                    elif action == "reject":
                        self.event.update(
                            {"ConditionalApproval": "auto-reject"}
                        )
                        route_table_approval_required[association_route_table][
                            "association_approval"
                        ] = True
            for propagation_route_table in propagation_route_tables:
                if route_table_approval_required[propagation_route_table].get(
                    "conditional_approval"
                ):
                    rule = route_table_approval_required[
                        propagation_route_table
                    ].get("rule")
                    if rule:
                        # action will be one of "accept|reject|approvalrequired"
                        action = self._process_conditional_approval_rule(
                            rule, route_type="Propagation"
                        )
                        self.logger.info(
                            f'Conditional rule result is "{action}" for propagation route table {propagation_route_table}'
                        )
                        if action == "accept":
                            route_table_approval_required[
                                propagation_route_table
                            ]["propagation_approval"] = False
                        elif action == "approvalrequired":
                            route_table_approval_required[
                                propagation_route_table
                            ]["propagation_approval"] = True
                        elif action == "reject":
                            self.event.update(
                                {"ConditionalApproval": "auto-reject"}
                            )
                            route_table_approval_required[
                                propagation_route_table
                            ]["propagation_approval"] = True

            # set approval on association changes
            if route_table_approval_required[association_route_table].get(
                "association_approval"
            ):
                # condition to check if already existing associated VPC settings are being changed.
                # example: change in propagation, add or remove subnet.
                if association_route_table == self.event.get(
                    "ExistingAssociationRouteTableId"
                ):
                    self.logger.info(
                        "Updating other setting for an existing association, no approval required."
                    )
                else:
                    self.logger.info(
                        "Found association route table that requires approval"
                    )
                    self.event.update({"ApprovalRequired": "yes"})
                    self.event.update({"AssociationNeedsApproval": "yes"})

            # set approval on propagation changes
            # iterate through the route table ids with enabled propagations routes tables
            # in the tagging event in the propagate-to key
            for route_table in propagation_route_tables:
                # check if this route table change requires approval
                if route_table_approval_required[route_table].get(
                    "propagation_approval"
                ):
                    self.logger.info(
                        "Found approval required tag on: {}".format(route_table)
                    )
                    if self.event.get(
                        "ExistingPropagationRouteTableIds"
                    ) is not None and route_table in self.event.get(
                        "ExistingPropagationRouteTableIds"
                    ):
                        self.logger.info(
                            "Route table: {} is in the existing propagation list,"
                            " NO approval required.".format(route_table)
                        )
                    else:
                        self.logger.info(
                            "Route table: {} is not in the existing propagation list. "
                            "Requires Approval.".format(route_table)
                        )
                        self.event.update({"ApprovalRequired": "yes"})
                        self.event.update({"PropagationNeedsApproval": "yes"})
                else:
                    self.logger.info(
                        ">>>>> Approval not required for Route Table: {}".format(
                            route_table
                        )
                    )

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _set_status(self):
        self.logger.info(
            EXECUTING + self.__class__.__name__ + "/" + inspect.stack()[0][3]
        )
        # needed for 'Requires Approval?' choice in state machine
        if (
            self.event.get("AdminAction") is None
        ):  # valid if VPC or Subnet will be tagged
            self.event.update(
                {"AdminAction": "not-applicable"}
            )  # set this value to match SM choice
            if self.event.get("ConditionalApproval") == "auto-reject":
                self.event.update(
                    {"Status": "auto-rejected"}
                )  # conditional approval auto-rejection
            elif (
                self.event.get("ApprovalRequired") == "yes"
            ):  # valid if RT is tagged with ApprovalRequired value
                self.event.update(
                    {"Status": "requested"}
                )  # adds the request to 'Action Items' console page
            elif self.event.get("ApprovalRequired") == "no":
                self.event.update(
                    {"Status": "auto-approved"}
                )  # adds the request to 'Dashboard' console page

        elif (
            self.event.get("AdminAction") == "accept"
        ):  # valid if event is coming from console action
            self.event.update(
                {"Status": "approved"}
            )  # adds the request to 'Dashboard' console page
        elif (
            self.event.get("AdminAction") == "reject"
        ):  # valid if event is coming from console action
            self.event.update(
                {"Status": "rejected"}
            )  # adds the request to 'Dashboard' console page

    def _extract_route_table_ids(
        self, associate_with_table, propagate_to_tables, response
    ):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            propagate_to_table_ids, rtb_list = [], []
            # Keep track of whether the given route table was found:
            association_table_not_found = True
            # Propagation is harder to keep track of as it's a list, any of which could be missing
            # So keep the propagate_to routeable table names in the list, and remove them as they are found:
            if propagate_to_tables:
                propagation_tables_that_are_not_found = (
                    propagate_to_tables.copy()
                )
            else:
                propagation_tables_that_are_not_found = []
            # If subnet is tagged before the VPC, the associations/propagations may not be set,
            # which is fine as we would still want the attachment to be created:
            if not associate_with_table:
                self.event.update({"AssociationRouteTableId": "none"})
                # No association expected,
                association_table_not_found = False

            for table in response:
                # make a list of Route Tables
                rtb_list.append(table.get("TransitGatewayRouteTableId"))
                # iterate through tags for each route table
                for tag in table.get("Tags"):
                    name_key = "Name"
                    # if tag key is 'Name' then match the value with extracted name from the event
                    if (
                        tag.get("Key").lower().strip()
                        == name_key.lower().strip()
                    ):
                        tag_name_value = tag.get("Value").lower().strip()
                        if (
                            associate_with_table
                            and tag_name_value == associate_with_table
                        ):
                            # extract route table id for association
                            association_table_not_found = False
                            self.logger.info(
                                "Association RTB Name found: {}".format(
                                    tag.get("Value")
                                )
                            )
                            self.event.update(
                                {
                                    "AssociationRouteTableId": table.get(
                                        "TransitGatewayRouteTableId"
                                    )
                                }
                            )
                        if (
                            propagate_to_tables
                            and tag_name_value in propagate_to_tables
                        ):
                            # extract route table id for propagation
                            propagation_tables_that_are_not_found.remove(
                                tag_name_value
                            )
                            self.logger.info(
                                "Propagation RTB Name Found: {}".format(
                                    tag.get("Value")
                                )
                            )
                            propagate_to_table_ids.append(
                                table.get("TransitGatewayRouteTableId")
                            )

            # Raise an exception if the route table was not found:
            if association_table_not_found:
                raise RouteTableNotFoundException(
                    f"RouteTableNotFoundException: The associate_with route table {associate_with_table} was not found."
                )
            if len(propagation_tables_that_are_not_found) > 0:
                raise RouteTableNotFoundException(
                    f"RouteTableNotFoundException: The propagate_to route tables {propagation_tables_that_are_not_found} was/were not found."
                )

            self.event.update(
                {"PropagationRouteTableIds": propagate_to_table_ids}
            )
            self.logger.info("RTB LIST: {}".format(rtb_list))
            return rtb_list
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _check_for_tgw_route_table_association(self, rtb_list, response):
        for rtb in rtb_list:
            # with the filters in the get API, the response list would always have one value, hence using [0]
            if (
                response
                and response[0]
                .get("Association", {})
                .get("TransitGatewayRouteTableId")
                == rtb
            ):
                # in case the response is empty
                # update the event with existing RT Id to compare with new RT Id
                self.logger.info(
                    f"Found existing association with route table: {rtb}"
                )
                self.event.update({"ExistingAssociationRouteTableId": rtb})

    def _find_existing_tgw_rt_association(self, ec2, rtb_list):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            self.event.update({"ExistingAssociationRouteTableId": "none"})
            # if transit gateway attachment id is not empty
            if self.event.get("TransitGatewayAttachmentId") is not None:
                response = ec2.describe_transit_gateway_attachments(
                    self.event.get("TransitGatewayAttachmentId")
                )
                self.logger.info(
                    f"Describe TGW Attachment Response: {response}"
                )

                # if route table list is not empty
                if rtb_list:
                    # Check if an existing TGW RT association exists
                    self._check_for_tgw_route_table_association(
                        rtb_list, response
                    )

                    # identify if the RT association should be created or updated
                    if self.event.get(
                        "AssociationRouteTableId"
                    ) == self.event.get("ExistingAssociationRouteTableId"):
                        self.logger.info(
                            "Existing Associated TGW RT and the New TGW RT Id match. No action required."
                        )
                        self.event.update(
                            {"UpdateAssociationRouteTableId": "no"}
                        )
                    else:
                        self.logger.info(
                            "New TGW RT association found in the event. Update association from {} to {}".format(
                                self.event.get(
                                    "ExistingAssociationRouteTableId"
                                ),
                                self.event.get("AssociationRouteTableId"),
                            )
                        )
                        self.event.update(
                            {"UpdateAssociationRouteTableId": "yes"}
                        )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _get_association_state(self, ec2, rtb, status):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            if status != "associated" or status != "disassociated":
                flag = True
            else:
                flag = False
            while flag:
                response = ec2.get_transit_gateway_route_table_associations(
                    rtb,
                    self.event.get("TransitGatewayAttachmentId"),
                    self.event.get("VpcId"),
                )
                self._print("Get TGW RT Association Response", response)
                # once the TGW RT is disassociated the returned response is empty list
                if response:
                    status = response[0].get("State")
                else:
                    self.logger.info(
                        "Found empty list, the TGW RT disassociated successfully."
                    )
                    status = "disassociated"
                self.logger.info("Status: {}".format(status))
                if status == "associated" or status == "disassociated":
                    flag = False
                self._print("Flag Value", flag)
                sleep(int(environ.get("WAIT_TIME")))
            return status
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def associate_transit_gateway_route_table(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = EC2()
            attachment_state = self.event.get("AttachmentState")
            association_route_table_id = self.event.get(
                "AssociationRouteTableId"
            )
            if association_route_table_id == None:
                self.logger.info(f"AssociationRouteTableId is empty, skipping.")
                return self.event
            # The attachment state is not the very latest,so try the association even if it's busy,
            # and if it fails, the step function will retry anyway:
            if attachment_state in (
                "available",
                "initiatingRequest",
                "modifying",
                "pending",
            ):
                self.logger.info(
                    f"Associating TGW Route Table Id: {association_route_table_id}"
                )
                self.event.update({"Action": "AssociateTgwRouteTable"})
                response = ec2.associate_transit_gateway_route_table(
                    association_route_table_id,
                    self.event.get("TransitGatewayAttachmentId"),
                )
                self._print("TGW Route Table Association Response", response)
                state = self._get_association_state(
                    ec2,
                    self.event.get("AssociationRouteTableId"),
                    response.get("Association").get("State"),
                )
                self.event.update({"AssociationState": state})
                self._create_tag(
                    self.event.get("VpcId"),
                    "VPCAssociation",
                    "VPC has been associated with the Transit Gateway Routing Table/Domain",
                )
            else:
                self.logger.info(
                    f"Not associating: the TGW-VPC Attachment is in state {attachment_state}"
                )
            return self.event
        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""

            if error_code == "Resource.AlreadyAssociated":
                # Another execution already configured this
                raise AlreadyConfiguredException
            elif error_code == "IncorrectState":
                # Attachment state is not available, try again later:
                raise ResourceBusyException

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def disassociate_transit_gateway_route_table(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = EC2()
            if self.event.get("AttachmentState") == "available":
                self.logger.info(
                    "Disassociating TGW Route Table Id: {}".format(
                        self.event.get("ExistingAssociationRouteTableId")
                    )
                )
                self.event.update({"Action": "DisassociateTgwRouteTable"})
                response = ec2.disassociate_transit_gateway_route_table(
                    self.event.get("ExistingAssociationRouteTableId"),
                    self.event.get("TransitGatewayAttachmentId"),
                )
                self._print("TGW Route Table Dissociation Response", response)
                state = self._get_association_state(
                    ec2,
                    self.event.get("ExistingAssociationRouteTableId"),
                    response.get("Association").get("State"),
                )
                self.event.update({"DisassociationState": state})
                self._create_tag(
                    self.event.get("VpcId"),
                    "VPCAssociation",
                    "VPC has been dissociated with the Transit Gateway Routing Table/Domain",
                )
            else:
                self.logger.info(TGW_VPC_ERROR)
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def get_transit_gateway_attachment_propagations(self):
        try:
            if self.event.get("AttachmentState") in ("available", "modifying"):
                self.logger.info(
                    EXECUTING
                    + self.__class__.__name__
                    + "/"
                    + inspect.stack()[0][3]
                )
                ec2 = EC2()
                response = ec2.get_transit_gateway_attachment_propagations(
                    self.event.get("TransitGatewayAttachmentId")
                )
                self._print(
                    "Get TGW Route Table Propagation Response", response
                )

                existing_route_table_list = []
                if response:
                    for item in response:
                        existing_route_table_list.append(
                            item.get("TransitGatewayRouteTableId")
                        )
                self.event.update(
                    {
                        "ExistingPropagationRouteTableIds": existing_route_table_list
                    }
                )
            else:
                self.logger.info(TGW_VPC_ERROR)
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _enable_rtb_list(self):
        event_set = set(self.event.get("PropagationRouteTableIds"))
        existing_set = set(
            self.event.get("ExistingPropagationRouteTableIds") or []
        )
        enable_rtb_list = list(event_set - event_set.intersection(existing_set))
        return enable_rtb_list

    def enable_transit_gateway_route_table_propagation(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = EC2()
            attachment_state = self.event.get("AttachmentState")
            enable_route_table_propagation = self._enable_rtb_list()
            if not enable_route_table_propagation:
                self.logger.info("No propagations to add, skipping")
                return self.event
            if attachment_state in (
                "available",
                "initiatingRequest",
                "modifying",
                "pending",
            ):
                self.event.update(
                    {
                        "EnablePropagationRouteTableIds": enable_route_table_propagation
                    }
                )
                # if the return list is empty the API to enable tgw rt propagation will be skipped.
                for tgw_route_table_id in enable_route_table_propagation:
                    self.logger.info(
                        "Enabling RT: {} Propagation To Tgw Attachment".format(
                            tgw_route_table_id
                        )
                    )
                    self.event.update({"Action": "EnableTgwRtPropagation"})
                    response = (
                        ec2.enable_transit_gateway_route_table_propagation(
                            tgw_route_table_id,
                            self.event.get("TransitGatewayAttachmentId"),
                        )
                    )
                    self._print(
                        "TGW Route Table Enable Propagation Response", response
                    )
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "VPC RT propagation has been enabled to the Transit Gateway Routing Table/Domain",
                    )
            else:
                self.logger.info(
                    f"The TGW-VPC Attachment is not in 'available', it is {attachment_state}"
                )
            return self.event
        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""

            if error_code == "TransitGatewayRouteTablePropagation.Duplicate":
                # Another execution already configured this
                raise AlreadyConfiguredException(e)
            elif error_code == "IncorrectState":
                # Cant apply right now
                raise ResourceBusyException(e)

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _disable_rtb_list(self):
        event_set = set(self.event.get("PropagationRouteTableIds"))
        existing_set = set(self.event.get("ExistingPropagationRouteTableIds"))
        disable_rtb_list = list(event_set.union(existing_set) - event_set)
        return disable_rtb_list

    def disable_transit_gateway_route_table_propagation(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = EC2()
            if self.event.get("AttachmentState") == "available":
                disable_route_table_propagation = self._disable_rtb_list()
                self.event.update(
                    {
                        "DisablePropagationRouteTableIds": disable_route_table_propagation
                    }
                )
                # if the return list is empty the API to disable tgw rt propagation will be skipped.
                for tgw_route_table_id in disable_route_table_propagation:
                    self.logger.info(
                        "Disabling RT: {} Propagation From Tgw Attachment".format(
                            tgw_route_table_id
                        )
                    )
                    self.event.update({"Action": "DisableTgwRtPropagation"})
                    response = (
                        ec2.disable_transit_gateway_route_table_propagation(
                            tgw_route_table_id,
                            self.event.get("TransitGatewayAttachmentId"),
                        )
                    )
                    self._print(
                        "TGW Route Table Disable Propagation Response", response
                    )
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "VPC RT propagation has been disabled from the "
                        "Transit Gateway Routing Table/Domain",
                    )
            else:
                self.logger.info(TGW_VPC_ERROR)
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def tag_transit_gateway_attachment(self):
        # Tags the Transit Gateway attachment with the key/values in "AttachmentTagsRequired"
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            transit_gateway_attachment_id = self.event.get(
                "TransitGatewayAttachmentId"
            )

            # Since the tags are not shared between the hub and spoke, we need to tag
            # both the hub account and the spoke account
            hub_ec2 = EC2()
            spoke_ec2 = self._session(self.spoke_account_id)

            for ec2 in (hub_ec2, spoke_ec2):
                # Get existing transit gateway attachment tags
                response = ec2.describe_transit_gateway_attachments(
                    transit_gateway_attachment_id
                )
                if len(response) == 0:
                    return self.event
                attachment = response[0]
                existing_tags = {
                    i["Key"]: i["Value"] for i in attachment.get("Tags")
                }
                required_tags = self.event.get("AttachmentTagsRequired")
                for key, val in required_tags.items():
                    if not key in existing_tags or existing_tags[key] != val:
                        self.logger.info(
                            f"Tagging attachment {transit_gateway_attachment_id} key {key} with value {val}"
                        )
                        ec2.create_tags(transit_gateway_attachment_id, key, val)

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def subnet_deletion_event(self):
        # This is an event from CloudTrail, so the location of the IDs in the event are different:
        try:
            detail = self.event.get("detail")
            subnet_id = detail.get("requestParameters", {}).get("subnetId")

            # Get the VPC ID from the spoke account::
            ec2 = self._session(self.spoke_account_id)
            response = ec2.describe_subnets(subnet_id)
            subnet = response[0]
            vpc_id = subnet.get("VpcId")

            # Get any available Transit Gateway VPC attachments for that VPC ID:
            attachments = ec2.describe_transit_gateway_vpc_attachments(
                tgw_id=environ.get("TGW_ID"),
                vpc_id=vpc_id,
                state=["available", "pending", "modifying"],
            )
            if len(attachments) == 0:
                # No attachments found, that's fine:
                return "No attachments found"
            # A transit gateway cannot have more than one attachment to the same VPC.
            attachment = attachments[0]

            # Verify that the subnet ID in question is one of the subnets in the VPC attachment:
            attachment_subnet_ids = attachment.get("SubnetIds")
            if subnet_id in attachment_subnet_ids:
                # Delete transit gateway attachment
                attachment_id = attachment.get("TransitGatewayAttachmentId")
                self.logger.info(
                    f"About to delete transit gateway VPC attachment {attachment_id}"
                )
                ec2.delete_transit_gateway_vpc_attachment(attachment_id)
                return f"Deleted transit gateway VPC attachment {attachment_id}"

            return (
                "No subnet IDs matched active transit gateway vpc attachments."
            )

        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""

            if (
                error_code == "InvalidVpcID.NotFound"
                or error_code == "InvalidSubnetID.NotFound"
            ):
                # This is fine, the subnet was already deleted
                return "Subnet or VPC already deleted"

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _update_ddb_failed(self, e):
        self.event.update({"Comment": str(e)})
        self.event.update({"Status": "failed"})
        ddb = DynamoDb(self.event)
        ddb.put_item()

    def _update_subnet_id_tags(self, subnet_id, error_message):
        subnet_tag_operations = [
            "CreateTransitGatewayVpcAttachment",
            "DeleteTransitGatewayVpcAttachment",
            "ModifyTransitGatewayVpcAttachment",
        ]
        for operation in subnet_tag_operations:
            if operation in error_message:
                self._create_tag(subnet_id, "Subnet-Error", error_message)

    def _update_vpc_id_tags(self, vpc_id, error_message):
        vpc_tag_operations = [
            "CreateTransitGatewayVpcAttachment",
            "DeleteTransitGatewayVpcAttachment",
            "ModifyTransitGatewayVpcAttachment",
            "AssociateTransitGatewayRouteTable",
            "DisassociateTransitGatewayRouteTable",
            "EnableTransitGatewayRouteTablePropagation",
            "DisableTransitGatewayRouteTablePropagation",
            "RouteTableNotFoundException",
        ]

        for operation in vpc_tag_operations:
            if operation in error_message:
                self._create_tag(vpc_id, "VPC-Error", error_message)

    def update_tags_if_failed(self):
        # This function updates the tags on the VPCs/Subnets, so that
        # the VPC owner has visibility on whether STNO failed.
        if self.event.get("Status", "") == "failed":
            error_message = self.event.get("Comment", "Unknown error")
            subnet_id = self.event.get("SubnetId")
            vpc_id = self.event.get("VpcId")
            if subnet_id:
                self._update_subnet_id_tags(subnet_id, error_message)
            if vpc_id:
                self._update_vpc_id_tags(vpc_id, error_message)
        return self.event


class VPC:
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.assume_role = AssumeRole()
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = self.event.get("region")
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)
        self.org_client = Organizations()

    def _session(self, account_id):
        # instantiate EC2 sessions
        return EC2(
            credentials=self.assume_role(account_id),
        )

    def _print(self, description, response):
        self.logger.info(f"Printing {description}")
        self.logger.info(response)

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)
            ec2.create_tags(
                resource, "STNOStatus-" + key, timestamp_message(message)
            )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def _extract_resource_id(self):
        self.logger.info(f"The event for resources is {self.event}")
        resource_arn = self.event.get("resources")[0]
        return resource_arn.split("/")[1]

    def _check_list_length(self, array, length):
        # compare the length of the list
        if len(array) == length:
            return None
        else:
            raise ValueError(
                "Length of the list in the response is more than {} values.".format(
                    length
                )
            )

    def _update_event_with_ou_name(self):
        """
        This method updates the event with on OU name and account name for tagging.
        """
        # Update the event with details on the account name and OU.
        account_id = self.event.get("account")
        if not account_id:
            account_id = self.event.get("AWSSpokeAccountId")
            if account_id:
                self.event.update({"account": account_id})

        account_name = self.org_client.get_account_name(account_id)
        if account_name:
            self.logger.debug(
                f"Updating the event with account name {account_name}"
            )
            self.event.update({"AccountName": account_name})

        account_ou_path = self.org_client.get_ou_path(account_id)
        if account_ou_path:
            self.logger.debug(
                f"Updating the event with OU path {account_ou_path}"
            )
            self.event.update({"AccountOuPath": account_ou_path})

    def _update_account_details(self):
        account_id = self.event.get("account")
        if not account_id:
            account_id = self.event.get("AWSSpokeAccountId")
            if account_id:
                self.event.update({"account": account_id})

        account_name = self.org_client.get_account_name(account_id)
        if account_name:
            self.event.update({"AccountName": account_name})

        account_ou_path = self.org_client.get_ou_path(account_id)
        if account_ou_path:
            self.event.update({"AccountOuPath": account_ou_path})
        self.logger.info("Updated Event with ou_name is: {}".format(self.event))

    def describe_resources(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            # Update the event with details on the account name and OU.
            # We first need the account ID:
            self._update_account_details()

            # check if the event is coming from STNO Management Console
            if self.event.get("AdminAction") is None:
                # extract subnet id from the ARN
                resource_id = self._extract_resource_id()
                # if event is from VPC tagging
                if resource_id.startswith("vpc"):
                    self.logger.info(
                        "Tag Change on VPC: {}".format(resource_id)
                    )
                    self.event.update({"VpcId": resource_id})
                    self.event.update({"TagEventSource": "vpc"})
                    # get VPC details
                    self._describe_vpc()
                # if event from Subnet tagging
                elif resource_id.startswith("subnet"):
                    self.logger.info(
                        "Tag Change on Subnet: {}".format(resource_id)
                    )
                    self.event.update({"SubnetId": resource_id})
                    self.event.update({"TagEventSource": "subnet"})
                    # get subnet details
                    self._describe_subnet()
                    # get VPC details
                    self._describe_vpc()
                else:
                    self.logger.info(
                        "Resource Id is neither a VPC nor a subnet."
                    )
                    raise TypeError(
                        "Application Exception: Resource Id is neither a VPC nor a subnet."
                    )
            elif self.event.get("TagEventSource") == "vpc":
                self._set_event_variables()
                # get VPC details
                self._describe_vpc()
            elif self.event.get("TagEventSource") == "subnet":
                self._set_event_variables()
                # get subnet details
                self._describe_subnet()
                # get VPC details
                self._describe_vpc()

            if self.event.get("time") is None:
                self.event.update({"time": current_time()})

            return self.event

        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""
            if (
                error_code == "InvalidVpcID.NotFound"
                or error_code == "InvalidSubnetID.NotFound"
            ):
                raise ResourceNotFoundException(e)

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _set_event_variables(self):
        self.logger.info(
            "Event came from the management console, setting variables"
        )
        self.event.update({"account": self.event.get("AWSSpokeAccountId")})
        self.event.update(
            {
                environ.get("ASSOCIATION_TAG"): self.event.get(
                    "AssociationRouteTable"
                )
            }
        )
        self.event.update(
            {
                environ.get("PROPAGATION_TAG"): self.event.get(
                    "PropagationRouteTables"
                )
            }
        )

        # re-initialize the class variables
        self._reset()

    def _reset(self):
        # reset class variables
        self.__init__(self.event)

    def _describe_vpc(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)

            # describe the vpc in the spoke account
            response = ec2.describe_vpcs(self.event.get("VpcId"))
            self._print("Describe VPC", response)

            # the response should return a list with single item
            self._check_list_length(response, 1)

            # update event with subnet details
            index = 0
            vpc = response[index]

            # Cidr block associated with this VPC
            self.event.update({"VpcCidr": vpc.get("CidrBlock")})

            # Assuming VPC is not tagged
            self.event.update({"VpcTagFound": "no"})

            tag_key_list = []
            if vpc.get("Tags") is not None:
                for tag in vpc.get("Tags"):
                    tag_key_list.append(tag.get("Key").lower().strip())
                self._print("list of tag keys", tag_key_list)
            else:
                self.logger.info(
                    "No tags found for the VPC associated with the tagged Subnet."
                )

            if (
                environ.get("ASSOCIATION_TAG").lower().strip() in tag_key_list
                or environ.get("PROPAGATION_TAG").lower().strip()
                in tag_key_list
            ):
                # check if tags exist for the VPC
                self.logger.info(
                    "Found association or propagation tag for the VPC: {}".format(
                        self.event.get("VpcId")
                    )
                )
                self.event.update({"VpcTagFound": "yes"})

            # event source is subnet tag change, then obtain the Tag Event Sources from VPC tags
            if self.event.get("TagEventSource") == "subnet":
                self._update_event_with_vpc_tags(vpc.get("Tags"))
            else:
                self._update_event_with_vpc_tags(
                    self.event.get("detail", {}).get("tags")
                )

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _match_keys_with_tag(self, key, value):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            if (
                key.lower().strip()
                == environ.get("ASSOCIATION_TAG").lower().strip()
            ):
                self.event.update(
                    {environ.get("ASSOCIATION_TAG"): value.lower().strip()}
                )
                self._print("Modified Event with Association Tag", self.event)
            elif (
                key.lower().strip()
                == environ.get("PROPAGATION_TAG").lower().strip()
            ):
                # organizations tag policy does not allow comma (,) as a
                # separator. Adding slash (/) and colon (:) as separators
                self.event.update(
                    {
                        environ.get("PROPAGATION_TAG"): [
                            x.lower().strip() for x in value.replace('/', ',').replace(':', ',').split(",")
                        ]
                    }
                )
                self._print("Modified Event with Propagation Tag", self.event)
            elif key.lower().strip() == "name":
                vpc_name = value.strip()
                self.logger.debug(
                    f"Updating the event with vpc name {vpc_name}"
                )
                self.event.update({"VpcName": vpc_name})

            if "AttachmentTagsRequired" not in self.event:
                self.event.update({"AttachmentTagsRequired": {}})

            # If the VPC_TAGS_FOR_ATTACHMENT is specified, and is not empty
            # go through this comma separated list, and see if the VPC has those tags.
            # If it does, store it in the event under AttachmentTagsRequired as a dictionary of key->value pairs.

            if "VPC_TAGS_FOR_ATTACHMENT" in environ:
                tag_keys_to_copy = environ.get("VPC_TAGS_FOR_ATTACHMENT").split(
                    ","
                )
                # Do a case insensitive match, example CostCode/codecode
                tag_keys_to_copy = [x.lower().strip() for x in tag_keys_to_copy]
                if key.lower().strip() in tag_keys_to_copy:
                    self.logger.debug(
                        f"Attaching tags with key {key} and value {value}"
                    )
                    self.event["AttachmentTagsRequired"][key] = value
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _update_event_with_tgw_attachment_name(self):
        """
        This method updates the event with a name for TGW attachment.
        """
        account_name = self.event.get("AccountName")
        self.logger.debug(f"account_name is: {account_name}")
        if account_name:
            self.event["AttachmentTagsRequired"]["account-name"] = account_name[
                :255
            ]

        account_ou_path = self.event.get("AccountOuPath")
        self.logger.debug(f"account_ou_path is {account_ou_path}")
        if account_ou_path:
            self.event["AttachmentTagsRequired"][
                "account-ou"
            ] = account_ou_path[:255]

        vpc_name = self.event.get("VpcName")
        self.logger.debug(f"VPC name is {vpc_name}")
        if vpc_name:
            self.event["AttachmentTagsRequired"][
                "vpc-name"
            ] = vpc_name[:255]

        # Construct the tgw Name tag. If we have the account_name: /The/Ou/Path/account_ame: vpc_name

        attachment_name = ""
        if account_ou_path:
            attachment_name += account_ou_path
        if account_name:
            attachment_name += f"{account_name}"
        if vpc_name:
            if account_ou_path or account_name:
                attachment_name = (
                    attachment_name + ": " + vpc_name
                )  # Add : to separate vpc name from ou/account
            else:
                attachment_name += vpc_name

        if attachment_name != "":  # If the name is not null tag it:
            truncated_attachment_name = attachment_name[:255]
            self.event["AttachmentTagsRequired"]["Name"] = truncated_attachment_name
            self.logger.debug(
                f"The appended TGW attachment is {truncated_attachment_name}"
            )

    def _update_event_with_vpc_tags(self, tags):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            self.logger.info(
                "Update event with VPC tags if the event source is 'Subnet'"
            )
            if isinstance(tags, list):
                for tag in tags:
                    self._match_keys_with_tag(tag.get("Key"), tag.get("Value"))
            elif isinstance(tags, dict):
                for key, value in tags.items():
                    self._match_keys_with_tag(key, value)

            if "AttachmentTagsRequired" not in self.event:
                self.event.update({"AttachmentTagsRequired": {}})

            self._update_event_with_tgw_attachment_name()
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _describe_subnet(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)

            # describe the subnet
            response = ec2.describe_subnets(self.event.get("SubnetId"))
            self._print("Describe Subnet", response)

            # the response should return a list with single item
            self._check_list_length(response, 1)

            # update event with subnet details
            index = 0
            subnet = response[index]

            # vpc id associated with this subnet
            self.event.update({"VpcId": subnet.get("VpcId")})

            # availability zone
            self.event.update(
                {"AvailabilityZone": subnet.get("AvailabilityZone")}
            )

            tag_key_list = []
            for tag in subnet.get("Tags"):
                tag_key_list.append(tag.get("Key").lower().strip())
            self._print("list of tag keys", tag_key_list)

            # check of tags exist for the subnet
            if environ.get("ATTACHMENT_TAG").lower().strip() in tag_key_list:
                self.logger.info(
                    "Found attachment tag for the subnet: {}".format(
                        self.event.get("SubnetId")
                    )
                )
                # help us decide if we can remove this subnet from the attachment
                self.event.update({"SubnetTagFound": "yes"})
            else:
                self.event.update({"SubnetTagFound": "no"})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _describe_route_tables_for_subnet(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)

            # describe the explicit route table association with the subnet
            response = ec2.describe_route_tables_for_subnet(
                self.event.get("SubnetId")
            )
            self._print("Describe Route Table for Subnets", response)

            # handle scenario of there is no EXPLICIT ASSOCIATION between the subnet and route table
            if len(response) != 0:
                # update event with subnet details
                index = 0
                route_table = response[index]

                # route table associated with this subnet
                self.event.update(
                    {"RouteTableId": route_table.get("RouteTableId")}
                )
                routes = route_table.get("Routes")
                return routes
            else:
                self.logger.info(
                    "There is no explicit route table association with the tagged subnet: {}".format(
                        self.event.get("SubnetId")
                    )
                )
                self.event.update({"RouteTableId": "No-Explicit-RT"})
                return None

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _find_existing_default_route(self, existing_routes, destination_route):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            gateway_id = None
            # set default flags
            self.event.update({"DefaultRouteToTgwExists": "no"})
            self.event.update({"DestinationRouteExists": "no"})
            for route in existing_routes:
                if route.get("DestinationCidrBlock") == destination_route:
                    # if destination route already exists in the route table - set flag
                    self.event.update({"DestinationRouteExists": "yes"})
                    self.logger.info(
                        "Found route: {} in the route table.".format(
                            destination_route
                        )
                    )
                    # Check if default route has Transit gateway as the target
                    if route.get("TransitGatewayId") is not None:
                        comment = "Found Transit Gateway as a target to the default route: {}".format(
                            destination_route
                        )
                        self.event.update({"DefaultRouteToTgwExists": "yes"})
                        self.logger.info(comment)
                        gateway_id = route.get("TransitGatewayId")
                        self._print("Transit Gateway Id", gateway_id)

                    # Check if default route has Internet gateway as the target
                    elif route.get("GatewayId") is not None:
                        comment = "Found existing gateway as a target to the default route: {}".format(
                            destination_route
                        )
                        self.logger.info(comment)
                        gateway_id = route.get("GatewayId")
                        self._print("Gateway Id", gateway_id)

                    # Check if default route has NAT gateway as the target
                    elif route.get("NatGatewayId") is not None:
                        comment = "Found NAT Gateway as a target to the default route: {}".format(
                            destination_route
                        )
                        self.logger.info(comment)
                        gateway_id = route.get("NatGatewayId")
                        self._print("NAT Gateway Id", gateway_id)
                    elif route.get("VpcPeeringConnectionId") is not None:
                        comment = "Found VPC Peering Connection as a target to the default route: {}".format(
                            destination_route
                        )
                        self.logger.info(comment)
                        gateway_id = route.get("VpcPeeringConnectionId")
                        self._print("Peering Connection Id", gateway_id)
                    else:
                        self.logger.info(
                            "Found an existing target for the default route."
                        )
                        gateway_id = "custom-target"
                        self._print("Route", route)
            # update event with gateway id
            self.event.update({"GatewayId": gateway_id})
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _create_route(self, ec2, destination):
        """
        This function creates routes in the route table associated with the
        tagged subnet.
        :param ec2: ec2 session
        :param destination: destination that would TGW as the
        target. Destination can be a CIDR block or prefix list.
        :return: None
        """
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            if (
                self.event.get("DefaultRouteToTgwExists") == "no"
                and self.event.get("DestinationRouteExists") == "no"
            ):
                self.logger.info(
                    f"Adding destination : {destination} to TGW gateway: "
                    f"{environ.get('TGW_ID')} into the route table:"
                    f" {self.event.get('RouteTableId')}"
                )
                if destination.startswith("pl-"):
                    ec2.create_route_prefix_list(
                        destination,
                        self.event.get("RouteTableId"),
                        environ.get("TGW_ID"),
                    )
                else:
                    ec2.create_route_cidr_block(
                        destination,
                        self.event.get("RouteTableId"),
                        environ.get("TGW_ID"),
                    )
                self._create_tag(
                    self.event.get("RouteTableId"),
                    "RouteTable",
                    "Route(s) added to the route table.",
                )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._create_tag(
                self.event.get("RouteTableId"), "RouteTable-Error", e
            )
            raise

    def _delete_route(self, ec2, destination):
        """
        This function deletes routes in the route table associated
        with the tagged subnet.
        :param ec2: ec2 session
        :param destination: destination that would TGW as the
        target. Destination can be a CIDR block or prefix list.
        :return: None
        """
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            if (
                self.event.get("DefaultRouteToTgwExists") == "yes"
                and self.event.get("DestinationRouteExists") == "yes"
            ):
                self.logger.info(
                    f"Removing destination : {destination} "
                    f"to TGW gateway: {environ.get('TGW_ID')}  "
                    f"from the route table:"
                    f" {self.event.get('RouteTableId')}"
                )
                if destination.startswith("pl-"):
                    ec2.delete_route_prefix_list(
                        destination, self.event.get("RouteTableId")
                    )
                else:
                    ec2.delete_route_cidr_block(
                        destination, self.event.get("RouteTableId")
                    )
                self._create_tag(
                    self.event.get("RouteTableId"),
                    "RouteTable",
                    "Route(s) removed from the route table.",
                )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._create_tag(
                self.event.get("RouteTableId"), "RouteTable-Error", e
            )
            raise

    def _update_route_table(self, ec2, route):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            # if adding subnet to tgw attachment - create route
            # else if removing subnet from tgw attachment - delete route
            if (
                self.event.get("Action") == "AddSubnet"
                or self.event.get("Action") == "CreateTgwVpcAttachment"
            ):
                # create route in spoke account route table
                self._create_route(ec2, route)
            elif (
                self.event.get("Action") == "RemoveSubnet"
                or self.event.get("Action") == "DeleteTgwVpcAttachment"
            ):
                # delete route from spoke account route table
                self._delete_route(ec2, route)
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def default_route_crud_operations(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            # this condition will be met if VPC tagged not Subnet

            if self.event.get("SubnetId") is not None:
                ec2 = self._session(self.spoke_account_id)

                existing_routes = self._describe_route_tables_for_subnet()

                # handles the case if the subnet has no association with
                # explicit route table
                if existing_routes is None:
                    return self.event

                # allowed values in hub CFN template
                # "All-Traffic (0/0)"
                # "RFC-1918 (10/8, 172.16/12, 192.168/16)"
                # "Custom Destinations"
                # "Configure-Manually
                quad_zero_route = environ.get("ALL_TRAFFIC")  # 0.0.0.0/0
                rfc_1918_routes = convert_string_to_list(
                    environ.get("RFC_1918_ROUTES")
                )

                if "All-Traffic" in environ.get("DEFAULT_ROUTE"):
                    self._find_existing_default_route(
                        existing_routes, quad_zero_route
                    )
                    self._update_route_table(ec2, quad_zero_route)
                elif "RFC-1918" in environ.get("DEFAULT_ROUTE"):
                    for route in rfc_1918_routes:
                        self._find_existing_default_route(
                            existing_routes, route
                        )
                        self._update_route_table(ec2, route)
                elif "Custom-Destinations" in environ.get("DEFAULT_ROUTE"):
                    self.update_route_table_with_cidr_blocks(
                        ec2, existing_routes
                    )
                    self.update_route_table_with_prefix_lists(
                        ec2, existing_routes
                    )

                elif "Configure-Manually" in environ.get("DEFAULT_ROUTE"):
                    self.logger.info(
                        "Admin opted to configure route table manually"
                    )

            return self.event

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def update_route_table_with_cidr_blocks(self, ec2, existing_routes):
        cidr_blocks = convert_string_to_list(environ.get("CIDR_BLOCKS"))
        if len(cidr_blocks) > 0:
            for route in cidr_blocks:
                self.logger.info(f"Adding route: {route}")
                self._find_existing_default_route(existing_routes, route)
                self._update_route_table(ec2, route)

    def update_route_table_with_prefix_lists(self, ec2, existing_routes):
        prefix_lists = convert_string_to_list(environ.get("PREFIX_LISTS"))
        if len(prefix_lists) > 0:
            for prefix_list_id in prefix_lists:
                self.logger.info(f"Adding prefix list id: {prefix_list_id}")
                self._find_existing_default_route(
                    existing_routes, prefix_list_id
                )
                self._update_route_table(ec2, prefix_list_id)

    def _message(self, method, e):
        return {
            "FILE": __file__.split("/")[-1],
            "CLASS": self.__class__.__name__,
            "METHOD": method,
            "EXCEPTION": str(e),
        }

    def _update_ddb_failed(self, e):
        self.event.update({"Comment": str(e)})
        self.event.update({"Status": "failed"})
        ddb = DynamoDb(self.event)
        ddb.put_item()


class DynamoDb:
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)

    def _get_time_to_live(self, time):
        utc_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        orig = datetime.fromtimestamp(int(epoch_time))
        ttl = orig + timedelta(days=int(environ.get("TTL")))
        return str(int((ttl - datetime(1970, 1, 1)).total_seconds()))

    # return None (string type) if the value is NoneType
    def is_none(self, value):
        if value is None:
            return "None"
        else:
            return value

    def put_item(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ddb = DDB(environ.get("TABLE_NAME"))

            # The SubnetId is the hash key for the table, and is used by the UI to get the latest event.
            # If there is a association/propagation tag change on an existing VPC already added to the TGW,
            # then the SubnetId will be empty (None), and thus the UI will show an entry for the latest
            # event with the SubnetId None set to the most recent VPC change, which will be overwritten with
            # newer VPC events. To prevent this, we try to populate the SubnetId with something, like the VpcId:
            if not self.event.get("SubnetId"):
                vpc_id = self.event.get("VpcId")
                if vpc_id:
                    self.event.update({"SubnetId": vpc_id})

            item = {
                "SubnetId": self.is_none(self.event.get("SubnetId")),
                "Version": self.is_none(
                    str(self.event.get("detail", {}).get("version"))
                ),
                "AvailabilityZone": self.is_none(
                    self.event.get("AvailabilityZone")
                ),
                "VpcId": self.is_none(self.event.get("VpcId")),
                "VpcName": self.is_none(self.event.get("VpcName")),
                "TgwId": self.is_none(environ.get("TGW_ID")),
                "PropagationRouteTables": self.event.get(
                    environ.get("PROPAGATION_TAG")
                ),
                "PropagationRouteTablesString": "None"
                if self.event.get(environ.get("PROPAGATION_TAG")) is None
                else ",".join(self.event.get(environ.get("PROPAGATION_TAG"))),
                "TagEventSource": self.is_none(
                    self.event.get("TagEventSource")
                ),
                "VpcCidr": self.is_none(self.event.get("VpcCidr")),
                "Action": self.is_none(self.event.get("Action")),
                "Status": self.is_none(self.event.get("Status")),
                "AWSSpokeAccountId": self.is_none(self.event.get("account")),
                "AWSSpokeAccountName": self.is_none(Organizations().get_account_name(self.event.get("account"))),
                "UserId": "StateMachine"
                if self.event.get("UserId") is None
                else self.event.get("UserId"),
                "AssociationRouteTable": self.event.get(
                    environ.get("ASSOCIATION_TAG")
                ),
                "RequestTimeStamp": self.event.get("time"),
                "ResponseTimeStamp": current_time()
                if self.event.get("GraphQLTimeStamp") is None
                else self.event.get("GraphQLTimeStamp"),
                "TimeToLive": self._get_time_to_live(self.event.get("time")),
                "Comment": self.is_none(self.event.get("Comment")),
            }

            self.logger.info(item)
            # add item to the DDB table with version in event
            ddb.put_item(item)

            item.update({"Version": "latest"})
            ddb.put_item(item)

            # send anonymous metrics
            gf = GeneralFunctions(self.event)
            gf.send_anonymous_data()

            return self.event
        except Exception as e:
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": inspect.stack()[0][3],
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            raise


class ApprovalNotification:
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = environ.get("AWS_REGION")
        self.assume_role = AssumeRole()
        self.account_name = Organizations().get_account_name(self.spoke_account_id)
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)

    def _session(self, account_id):
        # instantiate EC2 sessions
        return EC2(
            credentials=self.assume_role(account_id),
        )

    def notify(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            if (
                environ.get("APPROVAL_NOTIFICATION").lower() == "yes"
                and self.event.get("Status") == "requested"
            ):
                self._send_email()
                self.logger.info(
                    "Adding tag to VPC with the pending approval message"
                )
                if self.event.get("AssociationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCAssociation",
                        "Request to associate this VPC with requested TGW Routing Table is PENDING APPROVAL. "
                        "Contact your network admin for more information.",
                    )
                if self.event.get("PropagationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "Request to propagate this VPC to requested TGW Routing Table is PENDING APPROVAL. "
                        "Contact your network admin for more information.",
                    )
            elif (
                self.event.get("Status") == "rejected"
                or self.event.get("Status") == "auto-rejected"
            ):
                self.logger.info("Adding tag to VPC with the rejection message")
                if self.event.get("AssociationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCAssociation",
                        "Request to associate this VPC with requested TGW Routing Table has been REJECTED. "
                        "Contact your network admin for more information.",
                    )
                if self.event.get("PropagationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "Request to propagate this VPC to requested TGW Routing Table has been REJECTED. "
                        "Contact your network admin for more information. ",
                    )
            else:
                self.logger.info(
                    "Approval notifications are disabled. Please set CFN template variable "
                    "'ApprovalNotification' to 'Yes' if you wish to receive notifications."
                )
            return self.event
        except Exception as e:
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": inspect.stack()[0][3],
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _send_email(self):
        notify = SNS()
        topic_arn = environ.get("APPROVAL_NOTIFICATION_ARN")
        subject = "STNO: Transit Network Change Requested"
        message = (
            "A new request for VPC: '{}' from account {} to associate with TGW Route Table: '{}' and propagate to "
            "TGW Route Tables: '{}' is ready for review. Please use this link {} to login to the 'Transit Network "
            "Management Console' to approve or reject the request.".format(
                self.event.get("VpcId"),
                self.account_name or "N/A",
                self.event.get("Associate-with").title(),
                ", ".join(self.event.get("Propagate-to")).title(),
                environ.get("STNO_CONSOLE_LINK"),
            )
        )
        self.logger.info("Message: {}".format(message))
        notify.publish(topic_arn, message, subject)
        self.logger.info("Notfication sent to the network admin for approval.")

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._session(self.spoke_account_id)
            ec2.create_tags(
                resource, "STNOStatus-" + key, timestamp_message(message)
            )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def _message(self, method, e):
        return {
            "FILE": __file__.split("/")[-1],
            "CLASS": self.__class__.__name__,
            "METHOD": method,
            "EXCEPTION": str(e),
        }

    def _update_ddb_failed(self, e):
        self.event.update({"Comment": str(e)})
        self.event.update({"Status": "failed"})
        ddb = DynamoDb(self.event)
        ddb.put_item()


class ResourceAccessManager:
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.assume_role = AssumeRole()
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = self.event.get("region")
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return RAM(
            region,
            credentials=self.assume_role(account_id),
        )

    def _print(self, description, response):
        self.logger.info(f"Printing {description}")
        self.logger.info(response)

    def _hub_account_id(self):
        sts = STS()
        return sts.get_account_id()

    """ This function accepts resource invitation in the spoke account. This is applicable
     to the scenario if the accounts are not in the AWS Organization."""

    def accept_resource_share_invitation(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            # check if the accounts are in the organization
            check_invitation_status = True
            if "arn:aws:organizations" in environ.get("FIRST_PRINCIPAL"):
                check_invitation_status = False

            # check the invitation status if the accounts are not in AWS Organization
            if check_invitation_status:
                # accept resource share invitation
                ram = self._session(self.spoke_region, self.spoke_account_id)
                # get resource share invitations
                invitation_list = ram.get_resource_share_invitations(
                    environ.get("RESOURCE_SHARE_ARN")
                )
                self.logger.debug("Get Resource Share Invitation Response")
                self.logger.debug(
                    invitation_list
                )  # would always be single item in the response list
                for invitation in invitation_list:
                    # parse the invitation id arn to accept the invitation
                    if (
                        invitation.get("status") == "PENDING"
                        and invitation.get("senderAccountId")
                        == self._hub_account_id()
                    ):
                        response = ram.accept_resource_share_invitation(
                            invitation.get("resourceShareInvitationArn")
                        )
                        self._print("Accept Resource Share Response", response)
                        self.event.update(
                            {
                                "ResourceShareArnAccepted": invitation.get(
                                    "resourceShareArn"
                                )
                            }
                        )
                    else:
                        self.logger.info(
                            "PENDING resource share not found in the spoke account."
                        )
                        self.event.update(
                            {"ResourceShareArnAccepted": invitation.get("None")}
                        )
            return self.event
        except Exception as e:
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": inspect.stack()[0][3],
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            raise

    def _update_ddb_failed(self, e):
        self.event.update({"Comment": str(e)})
        self.event.update({"Status": "failed"})
        ddb = DynamoDb(self.event)
        ddb.put_item()


class GeneralFunctions:
    """
    This class contains functions that serves general purposes.
    """

    def __init__(self, event):
        self.event = event
        self.logger = logging.getLogger(__name__)
        self.logger.info(self.__class__.__name__ + CLASS_EVENT)
        self.logger.info(event)

    def _message(self, method, e):
        return {
            "FILE": __file__.split("/")[-1],
            "CLASS": self.__class__.__name__,
            "METHOD": method,
            "EXCEPTION": str(e),
        }

    # return None (string type) if the value is NoneType
    def is_none(self, value):
        if value is None:
            return "None"
        else:
            return value

    def send_anonymous_data(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            send = Metrics()
            data = {
                "Action": self.is_none(self.event.get("Action")),
                "Status": self.is_none(self.event.get("Status")),
                "AdminAction": self.is_none(self.event.get("AdminAction")),
                "ApprovalRequired": self.is_none(
                    self.event.get("ApprovalRequired")
                ),
                "TagEventSource": self.is_none(
                    self.event.get("TagEventSource")
                ),
                "Region": environ.get("AWS_REGION"),
                "SolutionVersion": self.is_none(
                    environ.get("SOLUTION_VERSION")
                ),
            }
            send.metrics(data)
            return self.event
        except Exception:
            return self.event

    def process_failure(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            # Add failure info:
            self.event.update({"Status": "failed"})
            # We're expecting the event to contain an 'error-info' with the Exception details
            error_info = self.event.get("error-info", {})
            error_message = ""
            try:
                cause = json.loads(error_info["Cause"])
                error_message = cause["errorMessage"]
            except Exception:
                error_message = str(error_info)

            self.event.update({"Comment": error_message})

            # Send failure to SNS topic:
            try:
                notify = SNS()
                topic_arn = environ.get("FAILURE_NOTIFICATIONS_TOPIC")
                subject = "STNO: Failure event"
                message = (
                    f"There has been a failed event in STNO. The error message is: {error_message}.\n\n"
                    "The complete event JSON is: \n\n"
                )
                event_str = json.dumps(self.event, indent=4)
                message += event_str
                notify.publish(topic_arn, message, subject)
            except Exception:
                # The rest of the steps (failure logging) would not complete
                # if this step fails, so continue:
                pass

            # sns.send()
            return self.event

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def log_in_cloudwatch(self):
        """
        This method puts logs for the success and failure events.
        """
        log_group_actions = environ.get("LOG_GROUP_ACTIONS")
        log_group_failures = environ.get("LOG_GROUP_FAILURES")
        cw_log = CloudWatchLogs()
        event_message = json.dumps(self.event)
        if self.event.get("Status", "") == "failed":
            self.logger.debug(
                f"Adding the message {event_message} to the log group {log_group_failures}"
            )
            cw_log.log(log_group_failures, event_message)
        else:
            self.logger.debug(
                f"Adding the message {event_message} to the log group {log_group_actions}"
            )
            cw_log.log(log_group_actions, event_message)
        return self.event
