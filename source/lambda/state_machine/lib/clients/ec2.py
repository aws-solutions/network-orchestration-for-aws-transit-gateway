# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Sequence, Union, List

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ec2.type_defs import DescribeVpcsResultTypeDef, VpcTypeDef, DescribeSubnetsResultTypeDef, SubnetTypeDef, \
    CreateRouteResultTypeDef, EmptyResponseMetadataTypeDef, DescribeRouteTablesResultTypeDef, RouteTableTypeDef, \
    AssociateTransitGatewayRouteTableResultTypeDef, CreateTransitGatewayVpcAttachmentResultTypeDef, \
    DeleteTransitGatewayVpcAttachmentResultTypeDef, DescribeTransitGatewayVpcAttachmentsResultTypeDef, \
    TransitGatewayVpcAttachmentTypeDef, DescribeTransitGatewayAttachmentsResultTypeDef, TransitGatewayAttachmentTypeDef, \
    DescribeTransitGatewayRouteTablesResultTypeDef, TransitGatewayRouteTableTypeDef, \
    DisableTransitGatewayRouteTablePropagationResultTypeDef, DisassociateTransitGatewayRouteTableResultTypeDef, \
    EnableTransitGatewayRouteTablePropagationResultTypeDef, GetTransitGatewayAttachmentPropagationsResultTypeDef, \
    TransitGatewayAttachmentPropagationTypeDef, GetTransitGatewayRouteTableAssociationsResultTypeDef, \
    TransitGatewayRouteTableAssociationTypeDef, ModifyTransitGatewayVpcAttachmentResultTypeDef, TagTypeDef

from state_machine.lib.clients.boto3_config import boto3_config


class EC2:

    def __init__(self, **kwargs):
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        if kwargs is not None:
            if kwargs.get("credentials") is None:
                self.logger.debug(
                    "Setting up EC2 BOTO3 Client with default credentials"
                )
                self.ec2_client: EC2Client = boto3.client("ec2", config=boto3_config)
            else:
                self.logger.debug(
                    "Setting up EC2 BOTO3 Client with ASSUMED ROLE credentials"
                )
                cred = kwargs.get("credentials")
                self.ec2_client: EC2Client = boto3.client(
                    "ec2",
                    config=boto3_config,
                    aws_access_key_id=cred.get("AccessKeyId"),
                    aws_secret_access_key=cred.get("SecretAccessKey"),
                    aws_session_token=cred.get("SessionToken"),
                )
        else:
            self.logger.info("There were no key worded variables passed.")
            self.ec2_client: EC2Client = boto3.client("ec2", config=boto3_config)

    def describe_vpcs(self, vpc_id: str) -> Union[List[VpcTypeDef], dict]:
        try:
            response: DescribeVpcsResultTypeDef = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
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

    def describe_subnets(self, subnet_id: str) -> list[SubnetTypeDef]:
        try:
            response: DescribeSubnetsResultTypeDef = self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
            subnet_list = response.get("Subnets", [])
            return subnet_list  # return list - should contain only one item in the list
        except Exception as error:
            self.logger.exception(
                f"Error while performing describe_subnets operation for subnet {subnet_id}"
            )
            self.logger.exception(error)
            raise

    def create_route_cidr_block(
            self,
            vpc_cidr: str,
            route_table_id: str,
            transit_gateway_id: str
    ) -> CreateRouteResultTypeDef:
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

    def delete_route_cidr_block(
            self,
            vpc_cidr: str,
            route_table_id: str
    ) -> EmptyResponseMetadataTypeDef:
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
            self,
            prefix_list: str,
            route_table_id: str,
            transit_gateway_id: str
    ) -> CreateRouteResultTypeDef:
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

    def delete_route_prefix_list(
            self,
            prefix_list: str,
            route_table_id: str):
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

    def describe_route_tables_for_subnet(
            self,
            subnet_id: str
    ) -> list[RouteTableTypeDef]:
        try:
            response: DescribeRouteTablesResultTypeDef = self.ec2_client.describe_route_tables(
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
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> AssociateTransitGatewayRouteTableResultTypeDef:
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

    def create_transit_gateway_vpc_attachment(
            self,
            tgw_id: str,
            vpc_id: str,
            subnet_id: str
    ) -> CreateTransitGatewayVpcAttachmentResultTypeDef:
        try:
            response: CreateTransitGatewayVpcAttachmentResultTypeDef = self.ec2_client.create_transit_gateway_vpc_attachment(
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

    def delete_transit_gateway_vpc_attachment(
            self,
            tgw_attachment_id: str
    ) -> DeleteTransitGatewayVpcAttachmentResultTypeDef:
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

    def get_transit_gateway_vpc_attachment_state(
            self,
            tgw_attachment_id: str
    ) -> list[TransitGatewayVpcAttachmentTypeDef]:
        try:
            response: DescribeTransitGatewayVpcAttachmentsResultTypeDef = self.ec2_client.describe_transit_gateway_vpc_attachments(
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

    def describe_transit_gateway_vpc_attachments(
            self,
            tgw_id: str,
            vpc_id: str,
            state
    ) -> list[TransitGatewayVpcAttachmentTypeDef]:
        """
        This method describes the transit gateway attachments for the specified vpc
        :param tgw_id: ID for the transit gateway
        :param vpc_id: ID for the VPC
        :param state: state for filtering attachments
        :return list of transit gateway vpc attachments
        """
        try:
            response: DescribeTransitGatewayVpcAttachmentsResultTypeDef = self.ec2_client.describe_transit_gateway_vpc_attachments(
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
            self, transit_gateway_attachment_id: str
    ) -> list[TransitGatewayAttachmentTypeDef]:
        try:
            response: DescribeTransitGatewayAttachmentsResultTypeDef = self.ec2_client.describe_transit_gateway_attachments(
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

    def describe_transit_gateway_route_tables(
            self,
            tgw_id: str
    ) -> list[TransitGatewayRouteTableTypeDef]:
        try:
            response: DescribeTransitGatewayRouteTablesResultTypeDef = self.ec2_client.describe_transit_gateway_route_tables(
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
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> DisableTransitGatewayRouteTablePropagationResultTypeDef:
        """
        This method disables transit gateway route propagations for specified tgw route table and tgw attachment
        :param transit_gateway_route_table_id: ID for the transit gateway route table
        :param transit_gateway_attachment_id: ID for the transit gateway attachment
        """
        try:
            response: DisableTransitGatewayRouteTablePropagationResultTypeDef = (
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
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> DisassociateTransitGatewayRouteTableResultTypeDef:
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
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> EnableTransitGatewayRouteTablePropagationResultTypeDef:
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
            self,
            transit_gateway_attachment_id: str
    ) -> list[TransitGatewayAttachmentPropagationTypeDef]:
        try:
            response: GetTransitGatewayAttachmentPropagationsResultTypeDef = (
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
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str,
            vpc_id: str
    ) -> list[TransitGatewayRouteTableAssociationTypeDef]:
        try:
            response: GetTransitGatewayRouteTableAssociationsResultTypeDef = (
                self.ec2_client.get_transit_gateway_route_table_associations(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    Filters=[
                        {
                            "Name": "transit-gateway-attachment-id",
                            "Values": [transit_gateway_attachment_id],
                        },
                        {"Name": "resource-type", "Values": ['vpc']},
                        {"Name": "resource-id", "Values": [vpc_id]},
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
                f"and resource id {vpc_id} "
            )
            self.logger.exception(error)
            raise

    def add_subnet_to_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ) -> Union[ModifyTransitGatewayVpcAttachmentResultTypeDef, dict]:
        try:
            response: ModifyTransitGatewayVpcAttachmentResultTypeDef = self.ec2_client.modify_transit_gateway_vpc_attachment(
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

    def remove_subnet_from_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ) -> ModifyTransitGatewayVpcAttachmentResultTypeDef:
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

    def create_tags(
            self,
            resource_id: str,
            tag_key: str,
            tag_value
    ) -> EmptyResponseMetadataTypeDef:
        try:
            response: EmptyResponseMetadataTypeDef = self.ec2_client.create_tags(
                Resources=[resource_id],
                Tags=[
                    {"Key": tag_key, "Value": tag_value},
                ],
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while creating tags with key "
                f"{tag_key} value {tag_value} and resource id {resource_id}"
            )
            self.logger.exception(error)
            raise

    def create_tags_batch(
            self,
            resource_id: str,
            tags_list: Sequence[TagTypeDef]
    ):
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
