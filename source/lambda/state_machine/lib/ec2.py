# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""EC2 module"""

import logging
import boto3
from botocore.exceptions import ClientError
from state_machine.lib.boto3_config import boto3_config


class EC2:
    """Class to handle EC2 methods"""

    def __init__(self, **kwargs):
        """Initialize the EC2 object's attributes"""
        self.logger = logging.getLogger(__name__)
        if kwargs is not None:
            if kwargs.get("credentials") is None:
                self.logger.debug(
                    "Setting up EC2 BOTO3 Client with default credentials"
                )
                self.ec2_client = boto3.client("ec2", config=boto3_config)
            else:
                self.logger.debug(
                    "Setting up EC2 BOTO3 Client with ASSUMED ROLE credentials"
                )
                cred = kwargs.get("credentials")
                self.ec2_client = boto3.client(
                    "ec2",
                    config=boto3_config,
                    aws_access_key_id=cred.get("AccessKeyId"),
                    aws_secret_access_key=cred.get("SecretAccessKey"),
                    aws_session_token=cred.get("SessionToken"),
                )
        else:
            self.logger.info("There were no key worded variables passed.")
            self.ec2_client = boto3.client("ec2", config=boto3_config)

    def describe_vpcs(self, vpc_id):
        """
        This method retrieves data for the given vpc
        :param vpc_id: ID of the VPC
        :return: list with vpc data
        """
        try:
            response = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            vpc_list = response.get("Vpcs", [])
            return vpc_list  # return list - should contain only one item in the list
        except ClientError as error:
            if error.response["Error"]["Code"] == "OptInRequired":
                self.logger.info(
                    "Caught exception 'OptInRequired', handling the exception..."
                )
                return {"Error": "OptInRequired"}
            else:
                self.logger.exception(
                    f"Error while performing describe_vpcs operation for vpc {vpc_id}"
                )
                self.logger.exception(error)
                raise

    def describe_subnets(self, subnet_id):
        """
        This method retrieves data for the given subnet
        :param subnet_id: ID of the subnet
        :return: list with subnet data
        """
        try:
            response = self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
            subnet_list = response.get("Subnets", [])
            return subnet_list  # return list - should contain only one item in the list
        except Exception as error:
            self.logger.exception(
                f"Error while performing describe_subnets operation for subnet {subnet_id}"
            )
            self.logger.exception(error)
            raise

    def create_route_cidr_block(
        self, vpc_cidr, route_table_id, transit_gateway_id
    ):
        """
        This method created route for the transit gateway in the given route table
        :param vpc_cidr: CIDR range for the VPC
        :param route_table_id: ID of the route table
        :param transit_gateway_id: ID of the Transit Gateway
        """
        try:
            response = self.ec2_client.create_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id,
                TransitGatewayId=transit_gateway_id,
            )
            return response
        except ClientError as error:
            self.logger.exception(
                f"Error while creating route for route table "
                f"{route_table_id}, vpc {vpc_cidr} and tgw {transit_gateway_id}"
            )
            self.logger.exception(error)
            raise

    def delete_route_cidr_block(self, vpc_cidr, route_table_id):
        """
        This method deletes route from the given route table
        :param vpc_cidr: CIDR range for the VPC
        :param route_table_id: ID for the route table
        """
        try:
            response = self.ec2_client.delete_route(
                DestinationCidrBlock=vpc_cidr, RouteTableId=route_table_id
            )
            return response
        except ClientError as error:
            self.logger.exception(
                f"Error while deleting the route for route table {route_table_id} and vpc {vpc_cidr}"
            )
            self.logger.exception(error)
            raise

    def create_route_prefix_list(
        self, prefix_list, route_table_id, transit_gateway_id
    ):
        """
        This method creates prefix list for the given route table
        :param prefix_list: Prefix list for the route table
        :param route_table_id: ID for the route table
        :param transit_gateway_id: ID for the transit gateway
        """
        try:
            response = self.ec2_client.create_route(
                DestinationPrefixListId=prefix_list,
                RouteTableId=route_table_id,
                TransitGatewayId=transit_gateway_id,
            )
            return response
        except ClientError as error:
            self.logger.exception(
                f"Error while creating route prefix list for route "
                f"table {route_table_id} and prefix list {prefix_list}"
            )
            self.logger.exception(error)
            raise

    def delete_route_prefix_list(self, prefix_list, route_table_id):
        """
        This method deletes prefix list for the given route table
        :param prefix_list: Prefix list for the route table
        :param route_table_id: ID for the route table
        """
        try:
            response = self.ec2_client.delete_route(
                DestinationPrefixListId=prefix_list, RouteTableId=route_table_id
            )
            return response
        except ClientError as error:
            self.logger.exception(
                f"Error while deleting route table prefix list for route "
                f"table {route_table_id} and prefix list {prefix_list}"
            )
            self.logger.exception(error)
            raise

    def describe_route_tables_for_subnet(self, subnet_id):
        """
        This method retrieves information about route tables for given subnet id
        :param subnet_id: ID for subnet
        :return list of route tables: Prefix list for the route table
        """
        try:
            response = self.ec2_client.describe_route_tables(
                Filters=[
                    {"Name": "association.subnet-id", "Values": [subnet_id]}
                ]
            )

            route_table_list = response.get("RouteTables", [])
            next_token = response.get("NextToken", None)

            while next_token is not None:
                response = self.ec2_client.describe_route_tables(
                    Filters=[
                        {"Name": "association.subnet-id", "Values": [subnet_id]}
                    ],
                    NextToken=next_token,
                )
                route_table_list.extend(response.get("RouteTables", []))
                next_token = response.get("NextToken", None)

            return route_table_list
        except Exception as error:
            self.logger.exception(
                f"Error while preforming describe information on subnet {subnet_id}"
            )
            self.logger.exception(error)
            raise

    def associate_transit_gateway_route_table(
        self, transit_gateway_route_table_id, transit_gateway_attachment_id
    ):
        """
        This method associates the specified attachment with the specified transit gateway route table
        :param transit_gateway_route_table_id: ID for the route table
        :param transit_gateway_attachment_id: ID for the transit gateway
        """
        try:
            response = self.ec2_client.associate_transit_gateway_route_table(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id,
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while associating attachment {transit_gateway_attachment_id} "
                f"with tgw route table {transit_gateway_route_table_id}"
            )
            self.logger.exception(error)
            raise

    def create_transit_gateway_vpc_attachment(self, tgw_id, vpc_id, subnet_id):
        """
        :param tgw_id:
        :param vpc_id:
        :param subnet_id:
        :return:
            {
            'TransitGatewayVpcAttachment': {
                'TransitGatewayAttachmentId': 'string',
                'TransitGatewayId': 'string',
                'VpcId': 'string',
                'VpcOwnerId': 'string',
                'State': 'pendingAcceptance'|'rollingBack'|'pending'|'available'|'modifying'|'deleting'|'deleted'
                |'failed'|'rejected'|'rejecting'|'failing',
                'SubnetIds': [
                    'string',
                ],
                'CreationTime': datetime(2015, 1, 1),
                'Options': {
                    'DnsSupport': 'enable'|'disable',
                    'Ipv6Support': 'enable'|'disable'
                },
                'Tags': [
                    {
                        'Key': 'string',
                        'Value': 'string'
                    },
                ]
            }
        }
        """
        try:
            response = self.ec2_client.create_transit_gateway_vpc_attachment(
                TransitGatewayId=tgw_id, VpcId=vpc_id, SubnetIds=[subnet_id]
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while creating transit gateway "
                f"vpc attachment for {tgw_id}, {vpc_id} and {subnet_id}"
            )
            self.logger.exception(error)
            raise

    def delete_transit_gateway_vpc_attachment(self, tgw_attachment_id):
        """
        :param tgw_attachment_id:
        :return:
            {
                'TransitGatewayVpcAttachment': {
                    'TransitGatewayAttachmentId': 'string',
                    'TransitGatewayId': 'string',
                    'VpcId': 'string',
                    'VpcOwnerId': 'string',
                    'State': 'pendingAcceptance'|'rollingBack'|'pending'|'available'|'modifying'|'deleting'|'deleted'
                    |'failed'|'rejected'|'rejecting'|'failing',
                    'SubnetIds': [
                        'string',
                    ],
                    'CreationTime': datetime(2015, 1, 1),
                    'Options': {
                        'DnsSupport': 'enable'|'disable',
                        'Ipv6Support': 'enable'|'disable'
                    },
                    'Tags': [
                        {
                            'Key': 'string',
                            'Value': 'string'
                        },
                    ]
                }
            }
        """
        try:
            response = self.ec2_client.delete_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while deleting transit gateway attachment {tgw_attachment_id} "
            )
            self.logger.exception(error)
            raise

    def get_transit_gateway_vpc_attachment_state(self, tgw_attachment_id):
        """
        This method retrieves state of transit gateway attachment
        :param tgw_attachment_id: ID for transit gateway attachment
        :return list of transit gateway vpc attachments
        """
        try:
            response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                TransitGatewayAttachmentIds=[tgw_attachment_id]
            )

            transit_gateway_vpc_attachments_list = response.get(
                "TransitGatewayVpcAttachments", []
            )
            next_token = response.get("NextToken", None)

            while next_token is not None:
                self.logger.info(f"Next Token Returned: {next_token}")
                response = (
                    self.ec2_client.describe_transit_gateway_vpc_attachments(
                        TransitGatewayAttachmentIds=[tgw_attachment_id],
                        NextToken=next_token,
                    )
                )
                self.logger.info("Extending TGW-VPC Attachment List")
                transit_gateway_vpc_attachments_list.extend(
                    response.get("TransitGatewayVpcAttachments", [])
                )
                next_token = response.get("NextToken", None)

            return transit_gateway_vpc_attachments_list

        except Exception as error:
            self.logger.exception(
                f"Error while retrieving the sate for tgw attachment {tgw_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def describe_transit_gateway_vpc_attachments(self, tgw_id, vpc_id, state):
        """
        This method describes the transit gateway attachments for the specified vpc
        :param tgw_id: ID for the transit gateway
        :param vpc_id: ID for the VPC
        :param state: state for filtering attachments
        :return list of transit gateway vpc attachments
        """
        try:
            response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                Filters=[
                    {"Name": "transit-gateway-id", "Values": [tgw_id]},
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "state", "Values": state},
                ]
            )

            transit_gateway_vpc_attachments_list = response.get(
                "TransitGatewayVpcAttachments", []
            )
            next_token = response.get("NextToken", None)

            while next_token is not None:
                self.logger.info(f"Next Token Returned: {next_token}")
                response = (
                    self.ec2_client.describe_transit_gateway_vpc_attachments(
                        Filters=[
                            {"Name": "transit-gateway-id", "Values": [tgw_id]},
                            {"Name": "vpc-id", "Values": [vpc_id]},
                            {"Name": "state", "Values": state},
                        ],
                        NextToken=next_token,
                    )
                )
                self.logger.info("Extending TGW-VPC Attachment List")
                transit_gateway_vpc_attachments_list.extend(
                    response.get("TransitGatewayVpcAttachments", [])
                )
                next_token = response.get("NextToken", None)

            return transit_gateway_vpc_attachments_list
        except Exception as error:
            self.logger.exception(
                f"Error while describing transit gateway attachments"
                f" for {tgw_id}, {vpc_id} and {state} "
            )
            self.logger.exception(error)
            raise

    def describe_transit_gateway_attachments(
        self, transit_gateway_attachment_id
    ):  # , tgw_id, vpc_id):
        """
        This method describes the transit gateway attachments for specified tgw attachment id
        :param transit_gateway_attachment_id: ID for the transit gateway attachment
        :return list of transit gateway attachments
        """
        try:
            response = self.ec2_client.describe_transit_gateway_attachments(
                TransitGatewayAttachmentIds=[transit_gateway_attachment_id]
            )

            transit_gateway_attachments_list = response.get(
                "TransitGatewayAttachments", []
            )
            next_token = response.get("NextToken", None)

            while next_token is not None:
                self.logger.info(f"Next Token Returned: {next_token}")
                response = self.ec2_client.describe_transit_gateway_attachments(
                    TransitGatewayAttachmentIds=[transit_gateway_attachment_id],
                    NextToken=next_token,
                )
                self.logger.info("Extending TGW Attachment List")
                transit_gateway_attachments_list.extend(
                    response.get("TransitGatewayAttachments", [])
                )
                next_token = response.get("NextToken", None)

            return transit_gateway_attachments_list
        except Exception as error:
            self.logger.exception(
                f"Error while performing describe operation for "
                f"tgw id {transit_gateway_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def describe_transit_gateway_route_tables(self, tgw_id):
        """
        This method describes the transit gateway route tables for specified tgw attachment id
        :param tgw_id: ID for transit gateway attachment
        :return list of route tables
        """
        try:
            response = self.ec2_client.describe_transit_gateway_route_tables(
                Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
            )

            route_table_list = response.get("TransitGatewayRouteTables", [])
            next_token = response.get("NextToken", None)

            while next_token is not None:
                response = (
                    self.ec2_client.describe_transit_gateway_route_tables(
                        Filters=[
                            {"Name": "transit-gateway-id", "Values": [tgw_id]}
                        ],
                        NextToken=next_token,
                    )
                )
                route_table_list.extend(
                    response.get("TransitGatewayRouteTables", [])
                )
                next_token = response.get("NextToken", None)
            return route_table_list
        except Exception as error:
            self.logger.exception(
                f"Error while describing transit gateway route tables for tgw_id {tgw_id}"
            )
            self.logger.exception(error)
            raise

    def disable_transit_gateway_route_table_propagation(
        self, transit_gateway_route_table_id, transit_gateway_attachment_id
    ):
        """
        This method disables transit gateway route propagations for specified tgw route table and tgw attachment
        :param transit_gateway_route_table_id: ID for the transit gateway route table
        :param transit_gateway_attachment_id: ID for the transit gateway attachment
        """
        try:
            response = (
                self.ec2_client.disable_transit_gateway_route_table_propagation(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    TransitGatewayAttachmentId=transit_gateway_attachment_id,
                )
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while disabling tgw route table propagation for tgw route table "
                f"{transit_gateway_route_table_id} and tgw attachment {transit_gateway_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def disassociate_transit_gateway_route_table(
        self, transit_gateway_route_table_id, transit_gateway_attachment_id
    ):
        """
        This method disassociates specified resource attachment from a transit gateway route table
        :param transit_gateway_route_table_id: ID for transit gateway route table
        :param transit_gateway_attachment_id: ID for transit gateway attachment
        """
        try:
            response = self.ec2_client.disassociate_transit_gateway_route_table(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id,
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while disassociating transit gateway route table "
                f"{transit_gateway_route_table_id} from attachment {transit_gateway_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def enable_transit_gateway_route_table_propagation(
        self, transit_gateway_route_table_id, transit_gateway_attachment_id
    ):
        """
        This method disables transit gateway route propagations for specified tgw route table and tgw attachment
        :param transit_gateway_route_table_id: ID for transit gateway route table
        :param transit_gateway_attachment_id: ID for transit gateway attachment
        """
        try:
            response = (
                self.ec2_client.enable_transit_gateway_route_table_propagation(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    TransitGatewayAttachmentId=transit_gateway_attachment_id,
                )
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while enabling transit gateway route propagation for tgw route table "
                f"{transit_gateway_route_table_id} and tgw attachment {transit_gateway_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def get_transit_gateway_attachment_propagations(
        self, transit_gateway_attachment_id
    ):
        """
        This method retrieves transit gateway propagations for specified transit gateway attachment id
        :param transit_gateway_attachment_id: ID for transit gateway attachment
        :return list of propagations
        """
        try:
            response = (
                self.ec2_client.get_transit_gateway_attachment_propagations(
                    TransitGatewayAttachmentId=transit_gateway_attachment_id
                )
            )
            propagations_list = response.get(
                "TransitGatewayAttachmentPropagations", []
            )
            next_token = response.get("NextToken", None)

            while next_token is not None:
                response = self.ec2_client.get_transit_gateway_attachment_propagations(
                    TransitGatewayAttachmentId=transit_gateway_attachment_id,
                    NextToken=next_token,
                )
                propagations_list.extend(
                    response.get("TransitGatewayAttachmentPropagations", [])
                )
                next_token = response.get("NextToken", None)
            return propagations_list
        except Exception as error:
            self.logger.exception(
                f"Error while retrieving transit gateway propagations for "
                f"tgw attachment id {transit_gateway_attachment_id}"
            )
            self.logger.exception(error)
            raise

    def get_transit_gateway_route_table_associations(
        self,
        transit_gateway_route_table_id,
        transit_gateway_attachment_id,
        resource_id,
        resource_type="vpc",
    ):
        """
        This method retrieves transit gateway route table associations
        :param transit_gateway_route_table_id: ID for transit gateway route table
        :param transit_gateway_attachment_id:ID for transit gateway attachment
        :param resource_id: VPC ID
        :return list of route table associations
        """
        try:
            response = (
                self.ec2_client.get_transit_gateway_route_table_associations(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    Filters=[
                        {
                            "Name": "transit-gateway-attachment-id",
                            "Values": [transit_gateway_attachment_id],
                        },
                        {"Name": "resource-type", "Values": [resource_type]},
                        {"Name": "resource-id", "Values": [resource_id]},
                    ],
                )
            )

            associations_list = response.get("Associations", [])
            next_token = response.get("NextToken", None)

            while next_token is not None:
                response = self.ec2_client.get_transit_gateway_route_table_associations(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    NextToken=next_token,
                )
                associations_list.extend(response.get("Associations", []))
                next_token = response.get("NextToken", None)
            return associations_list

        except Exception as error:
            self.logger.exception(
                f"Error while getting tgw route table associations for route table "
                f"{transit_gateway_route_table_id}, attachment id {transit_gateway_attachment_id} "
                f"and resource id {resource_id} "
            )
            self.logger.exception(error)
            raise

    def add_subnet_to_tgw_attachment(self, tgw_attachment_id, subnet_id):
        """
        This method adds subnet to the specified tgw attachment
        :param tgw_attachment_id: ID for transit gateway attachment
        :param subnet_id:
        """
        try:
            response = self.ec2_client.modify_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id,
                AddSubnetIds=[subnet_id],
            )
            return response
        except ClientError as error:
            if error.response["Error"]["Code"] == "IncorrectState":
                self.logger.info(
                    "Caught exception 'IncorrectState', handling the exception..."
                )
                return {"Error": "IncorrectState"}
            if error.response["Error"]["Code"] == "DuplicateSubnetsInSameZone":
                self.logger.info(
                    "Caught exception 'DuplicateSubnetsInSameZone', handling the exception..."
                )
                return {
                    "Error": "DuplicateSubnetsInSameZone",
                    "Message": str(error),
                }
            else:
                self.logger.exception(
                    f"Error while adding a subnet {subnet_id} "
                    f"to tgw attachment {tgw_attachment_id}"
                )
                self.logger.exception(error)
                raise

    def remove_subnet_from_tgw_attachment(self, tgw_attachment_id, subnet_id):
        """
        This method removes subnet from the specified tgw attachment
        :param tgw_attachment_id: ID for transit gateway attachment
        :param subnet_id: ID for subnet
        """
        try:
            response = self.ec2_client.modify_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id,
                RemoveSubnetIds=[subnet_id],
            )
            return response
        except ClientError as error:
            if error.response["Error"]["Code"] == "IncorrectState":
                self.logger.info(
                    "Caught exception 'IncorrectState', handling the exception..."
                )
                return {"Error": "IncorrectState"}
            elif (
                error.response["Error"]["Code"]
                == "InsufficientSubnetsException"
            ):
                self.logger.info(
                    "Caught exception 'InsufficientSubnetsException', handling the exception..."
                )
                return {"Error": "InsufficientSubnetsException"}
            else:
                self.logger.exception(
                    f"Error while removing subnet {subnet_id} "
                    f"from tgw attachment {tgw_attachment_id}"
                )
                self.logger.exception(error)
                raise

    def create_tags(self, resource_id, key, value):
        """
        This method creates tags with specified key and value
        :param resource_id: ID of the resource which needs to be tagged
        :param key: key for the tag
        :param value: value for the tag
        """
        try:
            response = self.ec2_client.create_tags(
                Resources=[resource_id],
                Tags=[
                    {"Key": key, "Value": value},
                ],
            )

            return response
        except Exception as error:
            self.logger.exception(
                f"Error while creating tags with key "
                f"{key} value {value} and resource id {resource_id}"
            )
            self.logger.exception(error)
            raise

    def create_tags_batch(self, resource_id, tags_list):
        """
        This method tags the resource with the list of tags
        :param resource_id: The resource id for the tagging
        :param tags_list: list of tags to be tagged for the resource
        """
        self.logger.debug(
            f"Tagging resource id {resource_id} with list of tags {tags_list}"
        )
        try:
            self.ec2_client.create_tags(Resources=[resource_id], Tags=tags_list)
            self.logger.debug(
                f"Successfully tagged resource id {resource_id} with list of tags {tags_list}"
            )
        except Exception as error:
            self.logger.exception(
                f"Failed to tag resource id {resource_id} with list of tags {tags_list} due to error {error}"
            )
            self.logger.exception(error)
