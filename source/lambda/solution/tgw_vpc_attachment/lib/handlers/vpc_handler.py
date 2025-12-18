# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from os import environ

from aws_lambda_powertools import Logger
from mypy_boto3_ec2.type_defs import RouteTableTypeDef

from solution.tgw_vpc_attachment.lib.clients.ec2 import EC2
from solution.tgw_vpc_attachment.lib.clients.organizations import Organizations
from solution.tgw_vpc_attachment.lib.clients.sts import STS
from solution.tgw_vpc_attachment.lib.exceptions import service_exception_handler
from solution.tgw_vpc_attachment.lib.handlers.tgw_vpc_attachment_model import TgwVpcAttachmentModel
from solution.tgw_vpc_attachment.lib.utils.helper import timestamp_message, current_time
from solution.tgw_vpc_attachment.lib.utils.list_utils import convert_string_to_list_with_no_whitespaces

EXECUTING = "Executing: "


class VPCHandler:
    def __init__(self, event: TgwVpcAttachmentModel):
        self.event: TgwVpcAttachmentModel = event
        self.association_tag = environ.get("ASSOCIATION_TAG")
        self.propagation_tag = environ.get("PROPAGATION_TAG")
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.org_client = Organizations()
        self._update_event_with_account_details()
        self.sts = STS()
        credentials = self.sts.assume_transit_network_execution_role(self.event.get("account"))
        self.spoke_ec2_client = EC2(credentials=credentials)
        self.logger.debug(event)

    @service_exception_handler
    def describe_resources(self):
        if self.event.get("AdminAction") is None:
            self._handle_event_from_tagging()
        else:
            self._handle_event_from_management_console()

        if self.event.get("time") is None:
            self.event.update({"time": current_time()})
        return self.event

    def _update_event_with_account_details(self):
        account_id = self.event.get("account")
        account_id = account_id if account_id else self.event.get("AWSSpokeAccountId")
        self.event.update({"account": account_id})

        account_name = self.org_client.get_account_name(account_id) if account_id else None
        if account_name:
            self.event.update({"AccountName": account_name})

        account_ou_path = self.org_client.get_ou_path(account_id) if account_id else None
        if account_ou_path:
            self.event.update({"AccountOuPath": account_ou_path})
        self.logger.debug(f"Updated Event with ou_name is: {self.event}")

    def _handle_event_from_tagging(self):
        # extract subnet id from the ARN
        resource_id = self._extract_resource_id()

        # if event is from VPC tagging
        if resource_id.startswith("vpc"):
            self.event.update({"VpcId": resource_id})
            self.event.update({"TagEventSource": "vpc"})
            self.event = VPCTagManager(self.event).update_event_with_vpc_details()

        # if event from Subnet tagging
        elif resource_id.startswith("subnet"):
            self.event.update({"SubnetId": resource_id})
            self.event.update({"TagEventSource": "subnet"})
            self._describe_subnet()
            self.event = VPCTagManager(self.event).update_event_with_vpc_details()

        else:
            raise TypeError(
                "Application Exception: Resource Id is neither a VPC nor a subnet."
            )

    def _handle_event_from_management_console(self):
        self._set_event_variables()
        self.event = VPCTagManager(self.event).update_event_with_vpc_details()
        if self.event.get("TagEventSource") == "subnet":
            self._describe_subnet()

    def _set_event_variables(self):
        self.logger.info(
            "Event came from the management console, setting variables"
        )
        self.event.update({"account": self.event.get("AWSSpokeAccountId")})
        self.event.update({self.association_tag: self.event.get("AssociationRouteTable")})
        self.event.update({self.propagation_tag: self.event.get("PropagationRouteTables")})

        # re-initialize the instance variables
        self.__init__(self.event)

    def _describe_subnet(self):
        # describe the subnet
        subnet = self.spoke_ec2_client.describe_subnets(self.event.get("SubnetId"))
        self.logger.debug("Describe Subnet", subnet)
        self.event.update({"VpcId": subnet.get("VpcId")})
        self.event.update({"AvailabilityZone": subnet.get("AvailabilityZone")})
        self.event.update({"SubnetTagFound": "no"})
        self._check_subnet_tags(subnet)

        return self.event

    def _check_subnet_tags(self, subnet):
        tag_key_list = dict()
        tags = subnet.get("Tags") or []  # Handle None case when subnet has no tags
        for tag in tags:
            tag_key_list[tag.get("Key").lower().strip()] = tag.get("Value").lower().strip()
        self.logger.debug(f"list of tag keys: {tag_key_list}")

        self.event.update({"SubnetTagFound": "no"})
        self.event.update({"MainRouteTableOnly": "no"})
        self._check_attach_to_tgw_tag(tag_key_list)
        self._check_route_to_tgw_tag(tag_key_list)

    def _check_attach_to_tgw_tag(self, tag_key_list):
        # checking if tag was create

        if environ.get("ATTACHMENT_TAG").lower().strip() in tag_key_list:
            self.logger.debug(f"Found attachment tag for the subnet: {self.event.get('SubnetId')}")
            self.event.update({"SubnetTagFound": "yes"})

    def _check_route_to_tgw_tag(self, tag_key_list):
        if environ.get("ROUTING_TAG").lower().strip() in tag_key_list:
            self.event.update({"SubnetTagFound": "yes"})
            self.event.update({"RouteToTgw": "create"})

        changed_tags = self.event.get('detail', {}).get('changed-tag-keys', [])
        route_to_tgw_tag_in_event = True if environ.get("ROUTING_TAG") in changed_tags else False

        if environ.get("ROUTING_TAG").lower().strip() not in tag_key_list and route_to_tgw_tag_in_event:
            self.event.update({"RouteToTgw": "delete"})

    def default_route_crud_operations(self):
        # this condition will be met if VPC is tagged and not is Subnet

        if self.event.get("SubnetId") is not None:
            existing_routes: list = self._describe_route_table_for_subnet()
            self.logger.debug(f"Returned routes: {existing_routes}")
            if not existing_routes:
                return self.event

            # allowed values in hub CFN template
            # "All-Traffic (0/0)"
            # "RFC-1918 (10/8, 172.16/12, 192.168/16)"
            # "Custom-Destinations"
            # "Configure-Manually

            if "All-Traffic" in environ.get("DEFAULT_ROUTE"):
                all_traffic_route = environ.get("ALL_TRAFFIC")  # 0.0.0.0/0
                self._find_existing_default_route(existing_routes, all_traffic_route)
                self._update_route_table(all_traffic_route)
            elif "RFC-1918" in environ.get("DEFAULT_ROUTE"):
                rfc_1918_routes = convert_string_to_list_with_no_whitespaces(environ.get("RFC_1918_ROUTES"))
                for route in rfc_1918_routes:
                    self._find_existing_default_route(existing_routes, route)
                    self._update_route_table(route)
            elif "Custom-Destinations" in environ.get("DEFAULT_ROUTE"):
                self._update_route_table_with_cidr_blocks(existing_routes)
                self._update_route_table_with_prefix_lists(existing_routes)
            elif "Configure-Manually" in environ.get("DEFAULT_ROUTE"):
                self.logger.info("Admin opted to configure route table manually")
        return self.event

    def _describe_route_table_for_subnet(self):
        subnet_id = self.event.get("SubnetId")
        route_tables: list[RouteTableTypeDef] = self.spoke_ec2_client.describe_route_tables_for_subnet(subnet_id)

        self.logger.debug(f"Describe Route Table for Subnets: {route_tables}")

        if len(route_tables) != 0:
            # update event with subnet details
            index = 0
            route_table = route_tables[index]

            # route table associated with this subnet
            self.event.update({"RouteTableId": route_table.get("RouteTableId")})
            self.event.update({"RouteTableType": "Explicit"})
            routes = route_table.get("Routes", [])
            return routes
        else:
            self.logger.info(
                f"No explicit route table association found for the tagged subnet: {subnet_id}, "
                f"returning main route table routes.")
            return self.get_routes_from_main_route_table()

    def get_routes_from_main_route_table(self):
        ec2 = self.spoke_ec2_client

        main_route_table = ec2.describe_main_route_table_id(self.event.get("VpcId"))
        self.event.update({"RouteTableId": main_route_table.get("RouteTableId")})
        self.event.update({"RouteTableType": "Main"})

        return main_route_table.get('Routes', [])

    def _update_route_table(self, route):
        # if adding subnet to tgw attachment - create route
        # else if removing subnet from tgw attachment - delete route
        if (
                self.event.get("Action") == "AddSubnet"
                or self.event.get("Action") == "CreateTgwVpcAttachment"
                or self.event.get("RouteToTgw") == "create"
        ):
            self._create_route(route)
        elif (
                self.event.get("Action") == "RemoveSubnet" and self.event.get("RouteTableType") == 'Explicit'
                or self.event.get("Action") == "DeleteTgwVpcAttachment"
                or self.event.get("RouteToTgw") == "delete"
        ):
            self._delete_route(route)

    def _create_route(self, destination):
        """
        This function creates routes in the route table associated with the
        tagged subnet.
        :param destination: destination that would TGW as the
        target. Destination can be a CIDR block or prefix list.
        :return: None
        """
        try:
            if (
                    self.event.get("DefaultRouteToTgwExists") == "no"
                    and self.event.get("DestinationRouteExists") == "no"
            ):
                self.logger.info(
                    f"Adding destination: {destination} to TGW gateway: "
                    f"{environ.get('TGW_ID')} into the route table:"
                    f" {self.event.get('RouteTableId')}"
                )
                if destination.startswith("pl-"):
                    self.spoke_ec2_client.create_route_prefix_list(
                        destination,
                        self.event.get("RouteTableId"),
                        environ.get("TGW_ID"),
                    )
                else:
                    self.spoke_ec2_client.create_route_cidr_block(
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
            self._create_tag(
                self.event.get("RouteTableId"), "RouteTable-Error", e
            )
            raise e

    def _delete_route(self, destination):
        """
        This function deletes routes in the route table associated
        with the tagged subnet.
        :param destination: destination that would TGW as the
        target. Destination can be a CIDR block or prefix list.
        :return: None
        """
        try:
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
                    self.spoke_ec2_client.delete_route_prefix_list(
                        destination, self.event.get("RouteTableId")
                    )
                else:
                    self.spoke_ec2_client.delete_route_cidr_block(
                        destination, self.event.get("RouteTableId")
                    )
                self._create_tag(
                    self.event.get("RouteTableId"),
                    "RouteTable",
                    "Route(s) removed from the route table.",
                )
        except Exception as e:
            self._create_tag(
                self.event.get("RouteTableId"), "RouteTable-Error", e
            )
            raise e

    def _update_route_table_with_cidr_blocks(self, existing_routes):
        cidr_blocks = convert_string_to_list_with_no_whitespaces(environ.get("CIDR_BLOCKS"))
        if len(cidr_blocks) > 0:
            for route in cidr_blocks:
                self.logger.debug(f"Adding route: {route}")
                self._find_existing_default_route(existing_routes, route)
                self._update_route_table(route)

    def _update_route_table_with_prefix_lists(self, existing_routes):

        prefix_lists = convert_string_to_list_with_no_whitespaces(environ.get("PREFIX_LISTS"))
        if len(prefix_lists) > 0:
            for prefix_list_id in prefix_lists:
                self.logger.info(f"Adding prefix list id: {prefix_list_id}")
                self._find_existing_default_route(
                    existing_routes, prefix_list_id
                )
                self._update_route_table(prefix_list_id)

    def _find_existing_default_route(self, existing_routes, destination_route):
        gateway_id = None
        self.event.update({"DefaultRouteToTgwExists": "no"})
        self.event.update({"DestinationRouteExists": "no"})
        for route in existing_routes:
            if route.get("DestinationCidrBlock") == destination_route:
                # if destination route already exists in the route table - set flag
                self.event.update({"DestinationRouteExists": "yes"})
                # Check if default route has Transit gateway as the target
                if route.get("TransitGatewayId") is not None:
                    comment = f"Found Transit Gateway as a target to the default route: {destination_route}"
                    self.event.update({"DefaultRouteToTgwExists": "yes"})
                    self.logger.debug(comment)
                    gateway_id = route.get("TransitGatewayId")
                    self.logger.debug(f"Transit Gateway Id: {gateway_id}")
                elif route.get("GatewayId") is not None:
                    comment = f"Found existing gateway as a target to the default route: {destination_route}"
                    self.logger.debug(comment)
                    gateway_id = route.get("GatewayId")
                    self.logger.debug(f"Gateway Id: {gateway_id}")
                elif route.get("NatGatewayId") is not None:
                    comment = f"Found NAT Gateway as a target to the default route: {destination_route}"
                    self.logger.info(comment)
                    gateway_id = route.get("NatGatewayId")
                    self.logger.debug(f"NAT Gateway Id: {gateway_id}")
                elif route.get("VpcPeeringConnectionId") is not None:
                    comment = f"Found VPC Peering Connection as a target to the default route: {destination_route}"
                    self.logger.info(comment)
                    gateway_id = route.get("VpcPeeringConnectionId")
                    self.logger.debug(f"Peering Connection Id: {gateway_id}")
                else:
                    self.logger.info("Found an existing target for the default route.")
                    gateway_id = "custom-target"
                    self.logger.debug("Route", route)
        self.event.update({"GatewayId": gateway_id})

    def _create_tag(self, resource, key, message, prefix=True):
        self.spoke_ec2_client.create_tags(
            resource, "STNOStatus-" + key, timestamp_message(message) if prefix else message
        )

    def _extract_resource_id(self):
        self.logger.info(f"The event for resources is {self.event}")
        resource_arn = self.event.get("resources")[0]
        return resource_arn.split("/")[1]


class VPCTagManager:
    def __init__(self, event: TgwVpcAttachmentModel):
        self.event = event
        self.association_tag = environ.get("ASSOCIATION_TAG")
        self.propagation_tag = environ.get("PROPAGATION_TAG")
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.sts = STS()
        self.logger.debug(event)
        credentials = self.sts.assume_transit_network_execution_role(self.event.get("account"))
        self.spoke_ec2_client = EC2(credentials=credentials)

    def update_event_with_vpc_details(self):
        vpc = self.spoke_ec2_client.describe_vpcs(self.event.get("VpcId"))

        # Cidr block associated with this VPC
        self.event.update({"VpcCidr": vpc.get("CidrBlock")})

        # Assuming VPC is not tagged
        self.event.update({"VpcTagFound": "no"})

        tags_keys_with_values = vpc.get("Tags")
        tag_keys_only = self._get_tag_keys(tags_keys_with_values)

        if (self.association_tag.lower().strip() in tag_keys_only
                or self.propagation_tag.lower().strip() in tag_keys_only):
            self.event.update({"VpcTagFound": "yes"})

        # event source is subnet tag change, then get the Tag Event Sources from VPC tags
        if self.event.get("TagEventSource") == "subnet":
            self._update_event_with_vpc_tags(tags_keys_with_values)
        else:
            self._update_event_with_vpc_tags(self.event.get("detail", {}).get("tags"))

        return self.event

    def _get_tag_keys(self, tags) -> list:
        tag_key_list = []
        if tags is not None:
            for tag in tags:
                tag_key_list.append(tag.get("Key").lower().strip())
            self.logger.debug("list of tag keys", tag_key_list)
        return tag_key_list

    def _update_event_with_vpc_tags(self, tags):
        self.logger.info("Update event with VPC tags if the event source is 'Subnet'")
        if isinstance(tags, list):
            for tag in tags:
                self._match_keys_with_tag(tag.get("Key"), tag.get("Value"))
        elif isinstance(tags, dict):
            for key, value in tags.items():
                self._match_keys_with_tag(key, value)

        if "AttachmentTagsRequired" not in self.event:
            self.event.update({"AttachmentTagsRequired": {}})

        self._update_event_with_tgw_attachment_name()

    def _update_event_with_tgw_attachment_name(self):
        account_name = self.event.get("AccountName")
        self.logger.debug(f"account_name is: {account_name}")
        if account_name:
            self.event["AttachmentTagsRequired"]["account-name"] = account_name[:255]

        account_ou_path = self.event.get("AccountOuPath")
        self.logger.debug(f"account_ou_path is {account_ou_path}")
        if account_ou_path:
            self.event["AttachmentTagsRequired"]["account-ou"] = account_ou_path[:255]

        vpc_name = self.event.get("VpcName")
        self.logger.debug(f"VPC name is {vpc_name}")
        if vpc_name:
            self.event["AttachmentTagsRequired"]["vpc-name"] = vpc_name[:255]

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

    def _match_keys_with_tag(self, key, value):
        # Store the original key before converting to lowercase
        original_key = key
        key_lower = key.lower().strip()

        # Use lowercase for comparison with solution-defined tags
        if key_lower == self.association_tag.lower().strip():
            self.event.update({self.association_tag: value.lower().strip()})
            self.logger.debug("Modified event with Association Tag", self.event)
        elif key_lower == self.propagation_tag.lower().strip():
            # organizations tag policy does not allow comma (,) as a
            # separator. Adding slash (/) and colon (:) as separators
            self.event.update({
                self.propagation_tag: [
                    x.lower().strip() for x in value.replace('/', ',').replace(':', ',').split(",")
                ]
            })
            self.logger.debug("Modified event with Propagation Tag", self.event)
        elif key_lower == "name":
            vpc_name = value.strip()
            self.logger.debug(f"Updating the event with vpc name {vpc_name}")
            self.event.update({"VpcName": vpc_name})

        if "AttachmentTagsRequired" not in self.event:
            self.event.update({"AttachmentTagsRequired": {}})

        # If the VPC_TAGS_FOR_ATTACHMENT is specified, and is not empty
        # go through this comma separated list, and see if the VPC has those tags.
        # If it does, store it in the event under AttachmentTagsRequired as a dictionary of key->value pairs.

        if "VPC_TAGS_FOR_ATTACHMENT" in environ:
            tag_keys_to_copy = environ.get("VPC_TAGS_FOR_ATTACHMENT").split(",")
            # Do a case insensitive match, example CostCode/costcode
            tag_keys_to_copy_lower = [x.lower().strip() for x in tag_keys_to_copy]
            if key_lower in tag_keys_to_copy_lower:
                self.logger.debug(f"Attaching tags with key {original_key} and value {value}")
                # Use the original key to preserve case sensitivity
                self.event["AttachmentTagsRequired"][original_key] = value
