# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from collections import Counter
from os import environ
from secrets import choice
from time import sleep
from typing import Tuple, List

from aws_lambda_powertools import Logger
from mypy_boto3_ec2.literals import TransitGatewayAttachmentStateType, TransitGatewayAssociationStateType
from mypy_boto3_ec2.type_defs import TransitGatewayRouteTableTypeDef

from tgw_vpc_attachment.lib.clients.ec2 import EC2
from tgw_vpc_attachment.lib.clients.sts import STS
from tgw_vpc_attachment.lib.exceptions import (
    ResourceBusyException,
    RouteTableNotFoundException, service_exception_handler,
)
from tgw_vpc_attachment.lib.handlers.approval_tag_handler import ApprovalTagHandler
from tgw_vpc_attachment.lib.handlers.tgw_vpc_attachment_model import TgwVpcAttachmentModel
from tgw_vpc_attachment.lib.utils.helper import timestamp_message

TGW_VPC_ERROR = "The TGW-VPC Attachment is not in 'available' state."


def throw_exception_if_duplicate_names(tgw_route_tables: List[
    TransitGatewayRouteTableTypeDef
]):
    # Extract the 'Name' tag values from all route tables
    route_table_names = [
        next((tag['Value'] for tag in tgw['Tags'] if tag['Key'].strip().lower() == 'name'),
             # use tgw id instead of name if there's no name tag. tgw id is unique in terms of duplicate detection.
             tgw['TransitGatewayRouteTableId'])
        for tgw in tgw_route_tables
    ]

    # Use collections.Counter to find duplicates
    name_counts = Counter(route_table_names)
    duplicates = [name for name, count in name_counts.items() if count > 1]

    # If duplicates are found, raise an exception
    if duplicates:
        raise ValueError(
            f"Invalid TGW route table setup. Multiple route tables are tagged with the name {', '.join(duplicates)}, which prevents deterministic TGW association. Please tag each route table with a unique name.")


class TransitGatewayVPCAttachments:

    def __init__(self, event: TgwVpcAttachmentModel):
        self.event = event  # careful, is being mutated and used as output parameter by methods
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.spoke_region = self.event.get("region")
        self.sts = STS()
        self.logger.debug(event)
        spoke_account_id = self.event.get("account")
        credentials = self.sts.assume_transit_network_execution_role(spoke_account_id)
        self.spoke_ec2_client = EC2(credentials=credentials)
        self.hub_ec2_client = EC2()

    def get_transit_gateway_vpc_attachment_state(self):
        # skip checking the TGW attachment status if it does not exist
        if self.event.get("TgwAttachmentExist").lower() == "yes":
            transit_gateway_vpc_attachment_state: TransitGatewayAttachmentStateType = \
                self.spoke_ec2_client.get_transit_gateway_vpc_attachment_state(
                    self.event.get("TransitGatewayAttachmentId")
                )
            self.event.update({"AttachmentState": transit_gateway_vpc_attachment_state})
            self.check_state_and_wait_for_random_time_to_avoid_race_condition(transit_gateway_vpc_attachment_state)
            self.logger.info(f"STATE : {transit_gateway_vpc_attachment_state}")
        return self.event

    @staticmethod
    def check_state_and_wait_for_random_time_to_avoid_race_condition(transit_gateway_vpc_attachment_state):
        if (
                transit_gateway_vpc_attachment_state == "pending"
                or transit_gateway_vpc_attachment_state == "modifying"
        ):
            _seconds = choice(range(5, 10))
            sleep(_seconds)

    def describe_transit_gateway_vpc_attachments(self):

        vpc_id = self.event.get("VpcId")
        tgw_id = environ.get("TGW_ID")
        response = self.spoke_ec2_client.describe_transit_gateway_vpc_attachments(
            tgw_id, vpc_id
        )
        attachment_state = "deleted"
        found_attachment = "no"

        if response:
            found_attachment = "yes"
            # check if the subnet is already in the TGW VPC Attachment
            for attachment in response:
                if attachment.get("VpcId") == vpc_id:
                    attachment_id = attachment.get("TransitGatewayAttachmentId")
                    attachment_state = attachment.get("State")
                    subnets_in_existing_vpc_attachment = attachment.get("SubnetIds")
                    subnet_id = self.event.get('SubnetId')
                    found_flag = "yes" if subnet_id in subnets_in_existing_vpc_attachment else "no"
                    self.event.update({"FoundExistingSubnetInAttachment": found_flag})
                    self.event.update({"TransitGatewayAttachmentId": attachment_id})

        self.event.update({"AttachmentState": attachment_state})
        self.event.update({"TgwAttachmentExist": found_attachment})
        return self.event

    def tgw_attachment_crud_operations(self):
        if (
                self.event.get("TgwAttachmentExist") == "no"
                and self.event.get("SubnetTagFound") == "yes"
        ):
            self._create_tgw_attachment()

        # update - add subnet to attachment
        if (
                self.event.get("FoundExistingSubnetInAttachment") == "no"
                and self.event.get("SubnetTagFound") == "yes"
        ):
            self._add_subnet_to_tgw_attachment()

        # update - remove subnet from attachment
        # OR
        # delete - if only one subnet left in attachment
        elif (
                self.event.get("FoundExistingSubnetInAttachment") == "yes"
                and self.event.get("SubnetTagFound") == "no"
        ):
            self._remove_subnet_from_tgw_attachment()
            self._create_tag(
                self.event.get('SubnetId'),
                "Subnet",
                "Subnet removed from the TGW attachment.",
            )

        # find existing TGW route table association to support update action
        self._find_existing_tgw_rt_association(
            self.spoke_ec2_client, self.event.get("RouteTableList")
        )

        return self.event

    @service_exception_handler
    def _create_tgw_attachment(self):
        self.logger.info(f"Creating TGW Attachment with Subnet ID: {self.event.get('SubnetId')}")
        response = self.spoke_ec2_client.create_transit_gateway_vpc_attachment(
            environ.get("TGW_ID"),
            self.event.get("VpcId"),
            self.event.get('SubnetId'),
        )
        # denormalize event - return dict
        # merge with event (cleaner)
        self.event.update({
            "AttachmentState": response.get("TransitGatewayVpcAttachment", {}).get("State")
        }
        )
        self.event.update(
            {
                "TransitGatewayAttachmentId": response.get(
                    "TransitGatewayVpcAttachment",
                    {}).get("TransitGatewayAttachmentId")
            }
        )
        self.event.update({"Action": "CreateTgwVpcAttachment"})
        self.event.update({"TgwAttachmentExist": "yes"})

        self._create_tag(
            self.event.get('SubnetId'),
            "Subnet",
            "Subnet added to the TGW attachment.",
        )
        self._create_tag(
            self.event.get("VpcId"),
            "VPCAttachment",
            "VPC has been attached to the Transit Gateway",
        )

    def _add_subnet_to_tgw_attachment(self):

        self.logger.info(f"Add Subnet: {self.event.get('SubnetId')} to Tgw Attachment")
        self.event.update({"Action": "AddSubnet"})
        response = self.spoke_ec2_client.add_subnet_to_tgw_attachment(
            self.event.get("TransitGatewayAttachmentId"),
            self.event.get('SubnetId'),
        )
        if response.get("Error") == "IncorrectState":
            raise ResourceBusyException
        elif response.get("Error") == "DuplicateSubnetsInSameZone":
            self.event.update({"Status": "auto-rejected"})
            comment = "You can only add one subnet in a TGW-VPC attachment per Availability Zone. Please delete and " \
                      "create the tag with RoutingTag provided in the Hub Template"
            self.event.update({"Comment": comment})
            self._create_tag(self.event.get("SubnetId"), "Subnet", comment)
        else:
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

    def _remove_subnet_from_tgw_attachment(self):

        self.logger.info(f"Remove Subnet: {self.event.get('SubnetId')} from"
                         f"Tgw Attachment: {self.event.get('TransitGatewayAttachmentId')}")
        self.event.update({"Action": "RemoveSubnet"})
        print(self.event)
        response = self.spoke_ec2_client.remove_subnet_from_tgw_attachment(
            self.event.get("TransitGatewayAttachmentId"),
            self.event.get('SubnetId'),
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
            self._delete_tgw_attachment()
        else:
            self.event.update(
                {
                    "AttachmentState": response.get(
                        "TransitGatewayVpcAttachment", {}
                    ).get("State")
                }
            )

    def _delete_tgw_attachment(self):

        # if this exception is thrown then it is safe to delete transit gateway attachment
        delete_response = self.spoke_ec2_client.delete_transit_gateway_vpc_attachment(
            self.event.get("TransitGatewayAttachmentId")
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

    # the function is called by a step function workflow triggered by a tag change.
    # the VPC has an associate-with tag with tgw route table name
    # and a propagate-to tag with multiple tgw route table names.
    # this function maps the route table names to route table ids and updates the event.
    # (careful, self.event is used as output parameter for functions that seem to return nothing.)
    def describe_transit_gateway_route_tables(self):

        # describe tgw route tables for the provided TGW ID
        tgw_id = environ.get("TGW_ID")
        tgw_route_tables: list[
            TransitGatewayRouteTableTypeDef
        ] = self.hub_ec2_client.describe_transit_gateway_route_tables(tgw_id)

        throw_exception_if_duplicate_names(tgw_route_tables)

        association_route_table_name, propagation_route_table_names = self._get_route_table_names_in_tags()
        self.logger.info(
            f"Table Names for the Association: {association_route_table_name} | Propagation:"
            f" {propagation_route_table_names}")

        # map route table names route table ids; throws exception if a name doesn't match a route table on the TGW
        route_table_ids: List[str] = self._get_route_table_ids_for_given_route_table_names(
            association_route_table_name, propagation_route_table_names, tgw_route_tables
        )
        self.event.update({"RouteTableList": route_table_ids})

        # find existing TGW route table association to support update action
        # needed for 'Association changed?' choice
        self._find_existing_tgw_rt_association(
            self.hub_ec2_client, self.event.get("RouteTableList")
        )

        # find existing TGW route table propagations
        self.get_transit_gateway_attachment_propagations()

        # set approval flag
        self.event = ApprovalTagHandler(self.event).analyze(tgw_route_tables)

        # set status based on the approval workflow
        self._set_approval_status()

        return self.event

    # looks at the tags in the input event and extracts the values of the association tag and propagation tag
    def _get_route_table_names_in_tags(self) -> Tuple[str | None, List]:
        association_tag = environ.get("ASSOCIATION_TAG").lower().strip()
        propagation_tag = environ.get("PROPAGATION_TAG").lower().strip()

        # look for defined tag keys in the event
        association_route_table_name_in_tags = None
        propagation_route_table_names_in_tags = []
        for k, value in self.event.items():  # value is a str or a List[str], depending on the case
            self.logger.debug(f"KEY: {k}, "
                              f"VALUE: {value}")
            key = k.lower().strip()
            if key == association_tag:
                self.logger.debug(
                    f"Key matched {association_tag}:")
                self.logger.debug(f"{k} : {value}")
                association_route_table_name_in_tags = value.lower().strip()
            elif key == propagation_tag:
                self.logger.debug(
                    f"Key matched {propagation_tag}:")
                self.logger.debug(f"{k}: {value}")
                propagation_route_table_names_in_tags = [x.lower().strip() for x in value]
        return association_route_table_name_in_tags, propagation_route_table_names_in_tags

    # this function maps the list of tgw_route_tables to a list of ids,
    # and validates the route table names in the given tags against the existing route tables on the TGW.
    # it also updates self.event as a side effect.
    # TODO split function to separate concerns
    def _get_route_table_ids_for_given_route_table_names(
            self,
            association_route_table_name: str | None,  # from tags
            propagation_route_table_names: List[str],  # from tags
            tgw_route_tables: list[TransitGatewayRouteTableTypeDef]
    ) -> List[str]:
        propagate_to_table_ids, tgw_route_table_ids = [], []
        # Keep track of whether the route table name in the associate-with tag exists on a TGW route table:
        association_table_not_found = True
        # Propagation is harder to keep track of as it's a list, any of which could be missing
        # So keep the propagate_to route table names in the list, and remove them as they are found:
        if propagation_route_table_names:
            propagation_tables_that_are_not_found = (
                propagation_route_table_names.copy()
            )
        else:
            propagation_tables_that_are_not_found = []
        # If subnet is tagged before the VPC, the associations/propagations may not be set,
        # in this case we still need to create the attachment.
        if not association_route_table_name:
            self.event.update({"AssociationRouteTableId": "none"})
            association_table_not_found = False

        for tgw_route_table in tgw_route_tables:
            # make a list of Route Table ids
            tgw_route_table_ids.append(tgw_route_table.get("TransitGatewayRouteTableId"))
            association_table_not_found, propagation_tables_that_are_not_found = self.check_tags_for_tgw_route_table(
                association_route_table_name,
                association_table_not_found,  # careful, used as output parameter
                propagate_to_table_ids,  # careful, used as output parameter
                propagation_route_table_names,
                propagation_tables_that_are_not_found,  # careful, used as output parameter
                tgw_route_table
            )

        # throw exception if 'associate-with' tag or 'propagate-to' tag contains a name that doesn't match any route table name of the TGW
        self.throw_if_not_found(association_route_table_name, association_table_not_found,
                                propagation_tables_that_are_not_found)
        self.event.update(
            {"PropagationRouteTableIds": propagate_to_table_ids}
        )
        self.logger.debug(f"TGW Route Tables: {tgw_route_table_ids}")
        return tgw_route_table_ids

    def check_tags_for_tgw_route_table(
            self,
            association_route_table_name: str | None,
            association_table_not_found: bool,  # careful, used as output parameter
            propagate_to_table_ids: List[str],  # careful, used as output parameter
            propagation_route_table_names: List[str],
            propagation_tables_that_are_not_found: List[str],  # careful, used as output parameter
            tgw_route_table: TransitGatewayRouteTableTypeDef
    ):
        # iterate through tags for each route table
        for tag in tgw_route_table.get("Tags"):
            # if tag key is 'Name' then match the value with extracted name from the event
            if tag.get("Key").lower().strip() == "name":
                route_table_name = tag.get("Value").lower().strip()
                if route_table_name == association_route_table_name:
                    # update event with route table id for association
                    association_table_not_found = False
                    self.logger.debug(f"Association RTB Name found: {tag.get('Value')}")
                    self.event.update(
                        {
                            "AssociationRouteTableId": tgw_route_table.get(
                                "TransitGatewayRouteTableId"
                            )
                        }
                    )
                if route_table_name in propagation_route_table_names:
                    # extract route table id for propagation
                    propagation_tables_that_are_not_found.remove(route_table_name)
                    self.logger.info(
                        f"Propagation RTB Name Found: {tag.get('Value')}")
                    propagate_to_table_ids.append(
                        tgw_route_table.get("TransitGatewayRouteTableId")
                    )
        return association_table_not_found, propagation_tables_that_are_not_found

    @staticmethod
    def throw_if_not_found(
            association_route_table_name, association_table_not_found,
            propagation_tables_that_are_not_found):
        if association_table_not_found:
            raise RouteTableNotFoundException(
                f"RouteTableNotFoundException: The associate_with route table "
                f"{association_route_table_name} was not found."
            )
        if len(propagation_tables_that_are_not_found) > 0:
            raise RouteTableNotFoundException(
                f"RouteTableNotFoundException: The propagate_to route tables "
                f"{propagation_tables_that_are_not_found} was/were not found."
            )

    def _find_existing_tgw_rt_association(self, ec2_client, rtb_list):

        self.event.update({"ExistingAssociationRouteTableId": "none"})
        # if transit gateway attachment id is not empty
        if self.event.get("TransitGatewayAttachmentId") is not None:
            response = ec2_client.describe_transit_gateway_attachments(
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
                    self.logger.debug(
                        f"New TGW RT association found in the event. Update association "
                        f"from {self.event.get('ExistingAssociationRouteTableId')} "
                        f"to {self.event.get('AssociationRouteTableId')}")
                    self.event.update(
                        {"UpdateAssociationRouteTableId": "yes"}
                    )

    def _check_for_tgw_route_table_association(self, rtb_list, response):
        for rtb in rtb_list:
            # with the filters in the get API, the response list would always have one value, hence using [0]
            if (
                    response
                    and response[0].get("Association", {})
                    .get("TransitGatewayRouteTableId")
                    == rtb
            ):
                # in case the response is empty
                # update the event with existing RT Id to compare with new RT Id
                self.logger.info(
                    f"Found existing association with route table: {rtb}"
                )
                self.event.update({"ExistingAssociationRouteTableId": rtb})

    def get_transit_gateway_attachment_propagations(self):
        if self.event.get("AttachmentState") in ("available", "modifying"):
            transit_gateway_attachment_id = self.event.get("TransitGatewayAttachmentId")
            response = self.hub_ec2_client.get_transit_gateway_attachment_propagations(transit_gateway_attachment_id)
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

    def _set_approval_status(self):
        # needed for 'Requires Approval?' choice in state machine
        status = 'undefined'
        if self.event.get("AdminAction") is None:  # valid if VPC or Subnet will be tagged
            self.event.update({"AdminAction": "not-applicable"})  # required for SM choice 'Requires Approval?'
            if self.event.get("ConditionalApproval") == "auto-rejected":
                status = "auto-rejected"
            elif self.event.get("ApprovalRequired") == "yes":  # valid if RT is tagged with ApprovalRequired value
                status = "requested"
            elif self.event.get("ApprovalRequired") == "no":
                status = "auto-approved"

        elif self.event.get("AdminAction") == "accept":  # valid if event is coming from console action
            status = "approved"  # adds the request to 'Dashboard' console page
        elif self.event.get("AdminAction") == "reject":  # valid if event is coming from console action
            status = "rejected"

        self.event.update({"Status": status})

    @service_exception_handler
    def associate_transit_gateway_route_table(self):
        attachment_state = self.event.get("AttachmentState")
        association_route_table_id = self.event.get("AssociationRouteTableId")
        if association_route_table_id is None:
            self.logger.info("AssociationRouteTableId is empty, skipping.")
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
            response = self.hub_ec2_client.associate_transit_gateway_route_table(
                association_route_table_id,
                transit_gateway_attachment_id,
            )
            state = self._get_association_state(
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

    def disassociate_transit_gateway_route_table(self):
        if self.event.get("AttachmentState") == "available":
            existing_association_route_table = self.event.get("ExistingAssociationRouteTableId")
            self.logger.info(f"Disassociating TGW Route Table Id: {existing_association_route_table}")
            self.event.update({"Action": "DisassociateTgwRouteTable"})
            response = self.hub_ec2_client.disassociate_transit_gateway_route_table(
                existing_association_route_table,
                self.event.get("TransitGatewayAttachmentId"),
            )
            state = self._get_association_state(
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

    def _get_association_state(self, rtb, state: TransitGatewayAssociationStateType):
        association_in_transient_state = False
        if state != "associated" or state != "disassociated":
            association_in_transient_state = True

        while association_in_transient_state:
            vpc_id = self.event.get("VpcId")
            tgw_attachment_id = self.event.get("TransitGatewayAttachmentId")
            response = self.hub_ec2_client.get_transit_gateway_route_table_associations(
                rtb,
                tgw_attachment_id,
                vpc_id,
            )
            # once the TGW RT is disassociated the returned response is empty list
            state = "disassociated"
            if response:
                state = response[0].get("State")
            self.logger.info(f"Association Status: {state}")
            if state == "associated" or state == "disassociated":
                association_in_transient_state = False
            sleep(int(environ.get("WAIT_TIME")))
        return state

    @service_exception_handler
    def enable_transit_gateway_route_table_propagation(self):
        attachment_state: TransitGatewayAttachmentStateType = self.event.get("AttachmentState")
        propagation_route_tables = self._get_propagation_route_tables_to_enable()

        if not propagation_route_tables:
            self.logger.info("No propagations to add, skipping")
            return self.event

        if attachment_state in (
                "available",
                "initiatingRequest",
                "modifying",
                "pending"
        ):
            self.event.update({"EnablePropagationRouteTableIds": propagation_route_tables})
            self.event.update({"Action": "EnableTgwRtPropagation"})

            # if the return list is empty the API to enable tgw rt propagation will be skipped.
            for tgw_route_table_id in propagation_route_tables:
                self.logger.info(f"Enabling RT: {tgw_route_table_id} Propagation To Tgw Attachment")
                response = self.hub_ec2_client.enable_transit_gateway_route_table_propagation(
                    tgw_route_table_id,
                    self.event.get("TransitGatewayAttachmentId"))

                if response.get("Error") == "IncorrectState":
                    raise ResourceBusyException

                self._create_tag(
                    self.event.get("VpcId"),
                    "VPCPropagation",
                    "VPC RT propagation has been enabled to the Transit Gateway Routing Table/Domain",
                )
        return self.event

    def _get_propagation_route_tables_to_enable(self):
        event_set = set(self.event.get("PropagationRouteTableIds"))
        existing_set = set(
            self.event.get("ExistingPropagationRouteTableIds") or []
        )
        enable_rtb_list = list(event_set - event_set.intersection(existing_set))
        return enable_rtb_list

    def disable_transit_gateway_route_table_propagation(self):
        if self.event.get("AttachmentState") == "available":
            propagation_route_tables = self._get_propagation_route_tables_to_disable()
            self.event.update(
                {
                    "DisablePropagationRouteTableIds": propagation_route_tables
                }
            )
            # if the return list is empty the API to disable tgw rt propagation will be skipped.
            for tgw_route_table_id in propagation_route_tables:
                self.logger.info(f"Disabling RT: {tgw_route_table_id} Propagation From Tgw Attachment")
                self.event.update({"Action": "DisableTgwRtPropagation"})
                self.hub_ec2_client.disable_transit_gateway_route_table_propagation(
                    tgw_route_table_id,
                    self.event.get("TransitGatewayAttachmentId"))
                self._create_tag(
                    self.event.get("VpcId"),
                    "VPCPropagation",
                    "VPC RT propagation has been disabled from the "
                    "Transit Gateway Routing Table/Domain",
                )
        else:
            self.logger.info(TGW_VPC_ERROR)
        return self.event

    def _get_propagation_route_tables_to_disable(self):
        event_set = set(self.event.get("PropagationRouteTableIds"))
        existing_set = set(self.event.get("ExistingPropagationRouteTableIds"))
        disable_rtb_list = list(event_set.union(existing_set) - event_set)
        return disable_rtb_list

    def tag_transit_gateway_attachment(self):
        # Tags the Transit Gateway attachment with the key/values in "AttachmentTagsRequired"

        transit_gateway_attachment_id = self.event.get(
            "TransitGatewayAttachmentId"
        )

        # Since the tags are not shared between the hub and spoke, we need to tag
        # both the hub account and the spoke account

        for ec2_client in (self.hub_ec2_client, self.spoke_ec2_client):
            # Get existing transit gateway attachment tags
            response = ec2_client.describe_transit_gateway_attachments(
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
                    ec2_client.create_tags(transit_gateway_attachment_id, key, val)

        return self.event

    @service_exception_handler
    def subnet_deletion_event(self):
        # This is an event from CloudTrail, so the location of the IDs in the event are different:
        detail = self.event.get("detail")
        subnet_id = detail.get("requestParameters", {}).get("subnetId")

        # Get the VPC ID from the spoke account::
        subnet = self.spoke_ec2_client.describe_subnets(subnet_id)
        vpc_id = subnet.get("VpcId")

        # Get any available Transit Gateway VPC attachments for that VPC ID:
        attachments = self.spoke_ec2_client.describe_transit_gateway_vpc_attachments(
            environ.get("TGW_ID"),
            vpc_id
        )

        if not attachments:
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
            self.spoke_ec2_client.delete_transit_gateway_vpc_attachment(attachment_id)
            return f"Deleted transit gateway VPC attachment {attachment_id}"

        return (
            "No subnet IDs matched active transit gateway vpc attachments."
        )

    def update_spoke_resource_tags_if_failed(self):
        if self.event.get("Status", "") == "failed":
            error_message = self.event.get("Comment", "Unknown error")
            subnet_id = self.event.get('SubnetId')
            vpc_id = self.event.get("VpcId")
            if subnet_id:
                self._update_subnet_id_tags(subnet_id, error_message)
            if vpc_id:
                self._update_vpc_id_tags(vpc_id, error_message)
        return self.event

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

    def _create_tag(self, resource, key, message):
        self.spoke_ec2_client.create_tags(
            resource,
            "STNOStatus-" + key,
            timestamp_message(message)
        )
