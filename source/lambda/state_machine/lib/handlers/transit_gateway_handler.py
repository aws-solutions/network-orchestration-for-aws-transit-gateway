# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import os
from os import environ
from secrets import choice
from time import sleep

from aws_lambda_powertools import Logger

from state_machine.lib.clients.ec2 import EC2
from state_machine.lib.clients.sts import STS
from state_machine.lib.exceptions import (
    AttachmentCreationInProgressException,
    AlreadyConfiguredException,
    ResourceBusyException,
    RouteTableNotFoundException,
)
from state_machine.lib.utils.helper import timestamp_message

EXECUTING = "Executing: "
TGW_VPC_ERROR = "The TGW-VPC Attachment is not in 'available'"


class TransitGateway:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = self.event.get("region")
        self.sts = STS()
        self.logger.info(event)

    def _ec2_client(self, account_id):
        credentials = self.sts.assume_transit_network_execution_role(account_id)
        return EC2(credentials=credentials)

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
            ec2 = self._ec2_client(self.spoke_account_id)
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
                ec2 = self._ec2_client(self.spoke_account_id)
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
            ec2 = self._ec2_client(self.spoke_account_id)
            states = ["available", "pending", "modifying"]
            vpc_id = self.event.get("VpcId")
            tgw_id = environ.get("TGW_ID")
            response = ec2.describe_transit_gateway_vpc_attachments(
                tgw_id, vpc_id, states
            )
            self._print("Transit Gateway Attachment List", response)

            if response:
                self.event.update({"TgwAttachmentExist": "yes"})

                # check if the subnet is already in the TGW VPC Attachment
                for attachment in response:
                    if attachment.get("VpcId") == vpc_id:
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
                        attached_subnets = attachment.get("SubnetIds")
                        subnet_id = self.event.get("SubnetId")
                        if subnet_id in attached_subnets:
                            self._print(
                                "subnet found in existing attachment",
                                subnet_id,
                            )
                            self.event.update(
                                {"FoundExistingSubnetInAttachment": "yes"}
                            )
                        else:
                            self._print(
                                "subnet list for existing TGW-VPC attachment",
                                attached_subnets,
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
            ec2 = self._ec2_client(self.spoke_account_id)

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
                vpc_id = self.event.get("VpcId")
                tgw_attachment_id = self.event.get("TransitGatewayAttachmentId")
                response = ec2.get_transit_gateway_route_table_associations(
                    rtb,
                    tgw_attachment_id,
                    vpc_id,
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
            association_route_table_id = self.event.get("AssociationRouteTableId")
            if association_route_table_id is None:
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
                transit_gateway_attachment_id = self.event.get("TransitGatewayAttachmentId")
                response = ec2.associate_transit_gateway_route_table(
                    association_route_table_id,
                    transit_gateway_attachment_id,
                )
                self._print("TGW Route Table Association Response", response)
                state = self._get_association_state(
                    ec2,
                    association_route_table_id,
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
                existing_association_route_table = self.event.get("ExistingAssociationRouteTableId")
                self.logger.info(
                    "Disassociating TGW Route Table Id: {}".format(
                        existing_association_route_table
                    )
                )
                self.event.update({"Action": "DisassociateTgwRouteTable"})
                response = ec2.disassociate_transit_gateway_route_table(
                    existing_association_route_table,
                    self.event.get("TransitGatewayAttachmentId"),
                )
                self._print("TGW Route Table Dissociation Response", response)
                state = self._get_association_state(
                    ec2,
                    existing_association_route_table,
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
                transit_gateway_attachment_id = self.event.get("TransitGatewayAttachmentId")
                response = ec2.get_transit_gateway_attachment_propagations(transit_gateway_attachment_id)
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
            spoke_ec2 = self._ec2_client(self.spoke_account_id)

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
                    if key not in existing_tags or existing_tags[key] != val:
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
            ec2 = self._ec2_client(self.spoke_account_id)
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
