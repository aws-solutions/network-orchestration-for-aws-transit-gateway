# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import os
from os import environ

from aws_lambda_powertools import Logger
from mypy_boto3_ec2.type_defs import RouteTableTypeDef

from state_machine.lib.clients.ec2 import EC2
from state_machine.lib.clients.organizations import Organizations
from state_machine.lib.clients.sts import STS
from state_machine.lib.exceptions import ResourceNotFoundException
from state_machine.lib.utils.helper import timestamp_message, current_time

EXECUTING = "Executing: "


class VPC:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.sts = STS()
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = self.event.get("region")
        self.logger.info(event)
        self.org_client = Organizations()

    def _ec2_client(self, account_id):
        credentials = self.sts.assume_transit_network_execution_role(account_id)
        return EC2(credentials=credentials)

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
            ec2 = self._ec2_client(self.spoke_account_id)
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

    def _update_event_with_account_details(self):
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

            self._update_event_with_account_details()

            if self.event.get("AdminAction") is None:
                self._handle_event_from_tagging()
            else:
                self._handle_event_from_management_console()

            if self.event.get("time") is None:
                self.event.update({"time": current_time()})

            return self.event

        except Exception as e:
            try:
                error_code = e.response["Error"]["Code"]
            except Exception:
                error_code = ""
            if (error_code == "InvalidVpcID.NotFound" or error_code == "InvalidSubnetID.NotFound"):
                raise ResourceNotFoundException(e)

            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _handle_event_from_tagging(self):
        # extract subnet id from the ARN
        resource_id = self._extract_resource_id()

        # if event is from VPC tagging
        if resource_id.startswith("vpc"):
            self.logger.info(
                "Tag Change on VPC: {}".format(resource_id)
            )
            self.event.update({"VpcId": resource_id})
            self.event.update({"TagEventSource": "vpc"})
            self._update_event_with_vpc_details()

        # if event from Subnet tagging
        elif resource_id.startswith("subnet"):
            self.logger.info(
                "Tag Change on Subnet: {}".format(resource_id)
            )
            self.event.update({"SubnetId": resource_id})
            self.event.update({"TagEventSource": "subnet"})
            self._describe_subnet()
            self._update_event_with_vpc_details()

        else:
            self.logger.info(
                "Resource Id is neither a VPC nor a subnet."
            )
            raise TypeError(
                "Application Exception: Resource Id is neither a VPC nor a subnet."
            )

    def _handle_event_from_management_console(self):
        self._set_event_variables()
        self._update_event_with_vpc_details()
        if self.event.get("TagEventSource") == "subnet":
            self._describe_subnet()

    def _set_event_variables(self):
        self.logger.info(
            "Event came from the management console, setting variables"
        )
        self.event.update({"account": self.event.get("AWSSpokeAccountId")})
        self.event.update({environ.get("ASSOCIATION_TAG"): self.event.get("AssociationRouteTable")})
        self.event.update({environ.get("PROPAGATION_TAG"): self.event.get("PropagationRouteTables")})

        # re-initialize the instance variables
        self.__init__(self.event)

    def _update_event_with_vpc_details(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2_spoke_client = self._ec2_client(self.spoke_account_id)

            response = ec2_spoke_client.describe_vpcs(self.event.get("VpcId"))
            self._print("Describe VPC", response)

            if len(response) > 1:
                raise ValueError("Length of the list in the response is more than 1 value.")

            # update event with subnet details
            index = 0
            vpc = response[index]

            # Cidr block associated with this VPC
            self.event.update({"VpcCidr": vpc.get("CidrBlock")})

            # Assuming VPC is not tagged
            self.event.update({"VpcTagFound": "no"})

            tag_key_list = []
            tags = vpc.get("Tags")
            if tags is not None:
                for tag in tags:
                    tag_key_list.append(tag.get("Key").lower().strip())
                self._print("list of tag keys", tag_key_list)

            if (
                    environ.get("ASSOCIATION_TAG").lower().strip() in tag_key_list
                    or environ.get("PROPAGATION_TAG").lower().strip() in tag_key_list
            ):
                # check if tags exist for the VPC
                self.logger.info(
                    "Found association or propagation tag for the VPC: {}".format(self.event.get("VpcId"))
                )
                self.event.update({"VpcTagFound": "yes"})

            # event source is subnet tag change, then obtain the Tag Event Sources from VPC tags
            if self.event.get("TagEventSource") == "subnet":
                self._update_event_with_vpc_tags(tags)
            else:
                self._update_event_with_vpc_tags(self.event.get("detail", {}).get("tags"))

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
            association_tag = environ.get("ASSOCIATION_TAG")
            propagation_tag = environ.get("PROPAGATION_TAG")
            key = key.lower().strip()

            if key == association_tag.lower().strip():
                self.event.update({association_tag: value.lower().strip()})
                self._print("Modified Event with Association Tag", self.event)
            elif key == propagation_tag.lower().strip():
                # organizations tag policy does not allow comma (,) as a
                # separator. Adding slash (/) and colon (:) as separators
                self.event.update({
                    propagation_tag: [
                        x.lower().strip() for x in value.replace('/', ',').replace(':', ',').split(",")
                    ]
                })
                self._print("Modified Event with Propagation Tag", self.event)
            elif key == "name":
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
                # Do a case insensitive match, example CostCode/codecode
                tag_keys_to_copy = [x.lower().strip() for x in tag_keys_to_copy]
                if key in tag_keys_to_copy:
                    self.logger.debug(f"Attaching tags with key {key} and value {value}")
                    self.event["AttachmentTagsRequired"][key] = value
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _update_event_with_tgw_attachment_name(self):
        account_name = self.event.get("AccountName")
        self.logger.debug(f"account_name is: {account_name}")
        if account_name:
            self.event["AttachmentTagsRequired"]["account-name"] = account_name[:255]

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
            ec2 = self._ec2_client(self.spoke_account_id)

            # describe the subnet
            response = ec2.describe_subnets(self.event.get("SubnetId"))
            self._print("Describe Subnet", response)

            if len(response) > 1:
                raise ValueError("Length of the list in the response is more than 1 value.")

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
            ec2 = self._ec2_client(self.spoke_account_id)

            # describe the explicit route table association with the subnet
            subnet_id = self.event.get("SubnetId")
            response: list[RouteTableTypeDef] = ec2.describe_route_tables_for_subnet(subnet_id)

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
                        subnet_id
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
                ec2 = self._ec2_client(self.spoke_account_id)

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

                if "All-Traffic" in environ.get("DEFAULT_ROUTE"):
                    all_traffic_route = environ.get("ALL_TRAFFIC")  # 0.0.0.0/0
                    self._find_existing_default_route(existing_routes, all_traffic_route)
                    self._update_route_table(ec2, all_traffic_route)
                elif "RFC-1918" in environ.get("DEFAULT_ROUTE"):
                    rfc_1918_routes = environ.get("RFC_1918_ROUTES").split(',')
                    for route in rfc_1918_routes:
                        self._find_existing_default_route(existing_routes, route)
                        self._update_route_table(ec2, route)
                elif "Custom-Destinations" in environ.get("DEFAULT_ROUTE"):
                    self._update_route_table_with_cidr_blocks(ec2, existing_routes)
                    self._update_route_table_with_prefix_lists(ec2, existing_routes)

                elif "Configure-Manually" in environ.get("DEFAULT_ROUTE"):
                    self.logger.info("Admin opted to configure route table manually")
            return self.event

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            raise

    def _update_route_table_with_cidr_blocks(self, ec2, existing_routes):
        cidr_blocks = environ.get("CIDR_BLOCKS").split(',')
        if len(cidr_blocks) > 0 and '' not in cidr_blocks:
            for route in cidr_blocks:
                route = route.lstrip()
                self.logger.info(f"Adding route: {route}")
                self._find_existing_default_route(existing_routes, route)
                self._update_route_table(ec2, route)

    def _update_route_table_with_prefix_lists(self, ec2, existing_routes):
        prefix_lists = environ.get("PREFIX_LISTS").split(',')
        if len(prefix_lists) > 0 and '' not in prefix_lists:
            for prefix_list_id in prefix_lists:
                prefix_list_id = prefix_list_id.lstrip()
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
