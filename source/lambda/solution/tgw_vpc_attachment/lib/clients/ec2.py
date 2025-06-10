# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Sequence, Union, List

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ec2.literals import TransitGatewayAttachmentStateType
from mypy_boto3_ec2.type_defs import DescribeVpcsResultTypeDef, VpcTypeDef, DescribeSubnetsResultTypeDef, \
    SubnetTypeDef, \
    CreateRouteResultTypeDef, EmptyResponseMetadataTypeDef, DescribeRouteTablesResultTypeDef, RouteTableTypeDef, \
    AssociateTransitGatewayRouteTableResultTypeDef, CreateTransitGatewayVpcAttachmentResultTypeDef, \
    DeleteTransitGatewayVpcAttachmentResultTypeDef, DescribeTransitGatewayVpcAttachmentsResultTypeDef, \
    TransitGatewayVpcAttachmentTypeDef, DescribeTransitGatewayAttachmentsResultTypeDef, \
    TransitGatewayAttachmentTypeDef, \
    DescribeTransitGatewayRouteTablesResultTypeDef, TransitGatewayRouteTableTypeDef, \
    DisableTransitGatewayRouteTablePropagationResultTypeDef, DisassociateTransitGatewayRouteTableResultTypeDef, \
    EnableTransitGatewayRouteTablePropagationResultTypeDef, GetTransitGatewayAttachmentPropagationsResultTypeDef, \
    TransitGatewayAttachmentPropagationTypeDef, GetTransitGatewayRouteTableAssociationsResultTypeDef, \
    TransitGatewayRouteTableAssociationTypeDef, ModifyTransitGatewayVpcAttachmentResultTypeDef, TagTypeDef

from solution.tgw_vpc_attachment.lib.clients.boto3_config import boto3_config
from solution.tgw_vpc_attachment.lib.exceptions import resource_exception_handler, service_exception_handler


class EC2:
    @service_exception_handler
    @resource_exception_handler
    def __init__(self, **kwargs):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
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

    @service_exception_handler
    @resource_exception_handler
    def describe_vpcs(self, vpc_id: str) -> Union[List[VpcTypeDef], dict]:
        response: DescribeVpcsResultTypeDef = self.ec2_client.describe_vpcs(
            VpcIds=[vpc_id]
        )
        vpc_list = response.get("Vpcs", [])
        self.logger.debug(response)
        if len(vpc_list) > 1:
            raise ValueError("Expected 1 value in describe_vpcs reponse.")
        return vpc_list[0]

    @service_exception_handler
    @resource_exception_handler
    def describe_subnets(self, subnet_id: str) -> SubnetTypeDef:
        response: DescribeSubnetsResultTypeDef = self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
        subnet_list = response.get("Subnets", [])
        self.logger.debug(subnet_list)
        self.logger.debug(response)
        if len(subnet_list) > 1:
            raise ValueError("Expected 1 value in describe_vpcs reponse.")
        return subnet_list[0]

    @service_exception_handler
    @resource_exception_handler
    def describe_main_route_table_id(self, vpc_id: str) -> RouteTableTypeDef:
        response: DescribeRouteTablesResultTypeDef = self.ec2_client.describe_route_tables(
            Filters=[
                {
                    "Name": "vpc-id",
                    "Values": [vpc_id]
                },
                {
                    "Name": "association.main",
                    "Values": ["true"]
                }
            ]
        )
        route_table_list = response.get("RouteTables", [])
        self.logger.debug(f"Main route table id: {route_table_list}")
        if len(route_table_list) > 1:
            raise ValueError("Expected 1 value in main route list")

        index = 0
        route_table = route_table_list[index]

        return route_table

    @service_exception_handler
    @resource_exception_handler
    def create_route_cidr_block(
            self,
            vpc_cidr: str,
            route_table_id: str,
            transit_gateway_id: str
    ) -> CreateRouteResultTypeDef:
        response = self.ec2_client.create_route(
            DestinationCidrBlock=vpc_cidr,
            RouteTableId=route_table_id,
            TransitGatewayId=transit_gateway_id,
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def delete_route_cidr_block(
            self,
            vpc_cidr: str,
            route_table_id: str
    ) -> EmptyResponseMetadataTypeDef:
        response = self.ec2_client.delete_route(
            DestinationCidrBlock=vpc_cidr, RouteTableId=route_table_id
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def create_route_prefix_list(
            self,
            prefix_list: str,
            route_table_id: str,
            transit_gateway_id: str
    ) -> CreateRouteResultTypeDef:
        response = self.ec2_client.create_route(
            DestinationPrefixListId=prefix_list,
            RouteTableId=route_table_id,
            TransitGatewayId=transit_gateway_id,
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def delete_route_prefix_list(
            self,
            prefix_list: str,
            route_table_id: str):
        response = self.ec2_client.delete_route(
            DestinationPrefixListId=prefix_list, RouteTableId=route_table_id
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def describe_route_tables_for_subnet(
            self,
            subnet_id: str
    ) -> list[RouteTableTypeDef]:
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
        self.logger.debug(f"Route Table List: {route_table_list}")
        return route_table_list

    @service_exception_handler
    @resource_exception_handler
    def associate_transit_gateway_route_table(
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> AssociateTransitGatewayRouteTableResultTypeDef:

        response = self.ec2_client.associate_transit_gateway_route_table(
            TransitGatewayRouteTableId=transit_gateway_route_table_id,
            TransitGatewayAttachmentId=transit_gateway_attachment_id,
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def create_transit_gateway_vpc_attachment(
            self,
            tgw_id: str,
            vpc_id: str,
            subnet_id: str
    ) -> CreateTransitGatewayVpcAttachmentResultTypeDef:
        tag_specifications = []
        # get tag key and value from environment variables
        tgw_attachment_tag_key = os.environ.get('APPLICATION_TAG_KEY')
        tgw_attachment_tag_value = os.environ.get('APPLICATION_TAG_VALUE')
        if  tgw_attachment_tag_key is not None and tgw_attachment_tag_value is not None:
            tag_specifications = [{
                'ResourceType': 'transit-gateway-attachment', # reference https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_TagSpecification.html
                'Tags': [
                    {
                        'Key': tgw_attachment_tag_key,
                        'Value': tgw_attachment_tag_value
                    }
                ]
            }]
        response: CreateTransitGatewayVpcAttachmentResultTypeDef = \
            self.ec2_client.create_transit_gateway_vpc_attachment(
                TransitGatewayId=tgw_id, VpcId=vpc_id, SubnetIds=[subnet_id],
                TagSpecifications=tag_specifications # AppRegistry application tags
            )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def delete_transit_gateway_vpc_attachment(
            self,
            tgw_attachment_id: str
    ) -> DeleteTransitGatewayVpcAttachmentResultTypeDef:
        response = self.ec2_client.delete_transit_gateway_vpc_attachment(
            TransitGatewayAttachmentId=tgw_attachment_id
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def get_transit_gateway_vpc_attachment_state(
            self,
            tgw_attachment_id: str
    ) -> TransitGatewayAttachmentStateType:
        response: DescribeTransitGatewayVpcAttachmentsResultTypeDef = \
            self.ec2_client.describe_transit_gateway_vpc_attachments(
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
        self.logger.debug(transit_gateway_vpc_attachments_list)
        # the list should always contain a single item
        return transit_gateway_vpc_attachments_list[0].get("State")

    @service_exception_handler
    @resource_exception_handler
    def describe_transit_gateway_vpc_attachments(
            self,
            tgw_id: str,
            vpc_id: str,
    ) -> list[TransitGatewayVpcAttachmentTypeDef]:
        state = ["available", "pending", "modifying"]
        response: DescribeTransitGatewayVpcAttachmentsResultTypeDef = \
            self.ec2_client.describe_transit_gateway_vpc_attachments(
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
        self.logger.debug(transit_gateway_vpc_attachments_list)

        return transit_gateway_vpc_attachments_list

    @service_exception_handler
    @resource_exception_handler
    def describe_transit_gateway_attachments(
            self, transit_gateway_attachment_id: str
    ) -> list[TransitGatewayAttachmentTypeDef]:
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
        self.logger.debug(transit_gateway_attachments_list)
        return transit_gateway_attachments_list

    @service_exception_handler
    @resource_exception_handler
    def describe_transit_gateway_route_tables(
            self,
            tgw_id: str
    ) -> list[TransitGatewayRouteTableTypeDef]:
        response: DescribeTransitGatewayRouteTablesResultTypeDef = \
            self.ec2_client.describe_transit_gateway_route_tables(
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
        self.logger.debug(route_table_list)
        return route_table_list

    @service_exception_handler
    @resource_exception_handler
    def disable_transit_gateway_route_table_propagation(
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> DisableTransitGatewayRouteTablePropagationResultTypeDef:
        response: DisableTransitGatewayRouteTablePropagationResultTypeDef = (
            self.ec2_client.disable_transit_gateway_route_table_propagation(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id,
            )
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def disassociate_transit_gateway_route_table(
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> DisassociateTransitGatewayRouteTableResultTypeDef:
        response = self.ec2_client.disassociate_transit_gateway_route_table(
            TransitGatewayRouteTableId=transit_gateway_route_table_id,
            TransitGatewayAttachmentId=transit_gateway_attachment_id,
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def enable_transit_gateway_route_table_propagation(
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str
    ) -> EnableTransitGatewayRouteTablePropagationResultTypeDef:
        response = (
            self.ec2_client.enable_transit_gateway_route_table_propagation(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id,
            )
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def get_transit_gateway_attachment_propagations(
            self,
            transit_gateway_attachment_id: str
    ) -> list[TransitGatewayAttachmentPropagationTypeDef]:
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
        self.logger.debug(propagations_list)
        return propagations_list

    @service_exception_handler
    @resource_exception_handler
    def get_transit_gateway_route_table_associations(
            self,
            transit_gateway_route_table_id: str,
            transit_gateway_attachment_id: str,
            vpc_id: str
    ) -> list[TransitGatewayRouteTableAssociationTypeDef]:
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
        self.logger.debug(associations_list)
        return associations_list

    @service_exception_handler
    @resource_exception_handler
    def add_subnet_to_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ) -> Union[ModifyTransitGatewayVpcAttachmentResultTypeDef, dict]:
        response: ModifyTransitGatewayVpcAttachmentResultTypeDef = \
            self.ec2_client.modify_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id,
                AddSubnetIds=[subnet_id],
            )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def remove_subnet_from_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ) -> Union[ModifyTransitGatewayVpcAttachmentResultTypeDef, dict]:
        response = self.ec2_client.modify_transit_gateway_vpc_attachment(
            TransitGatewayAttachmentId=tgw_attachment_id,
            RemoveSubnetIds=[subnet_id],
        )
        self.logger.debug(response)
        return response

    @service_exception_handler
    @resource_exception_handler
    def create_tags(
            self,
            resource_id: str,
            tag_key: str,
            tag_value
    ) -> None:
        self.logger.debug(f"Creating Tag:"
                          f"Resource: {resource_id}; "
                          f"Tag Key: {tag_key}; "
                          f"Tag Value: {tag_value}")
        self.ec2_client.create_tags(
            Resources=[resource_id],
            Tags=[{
                "Key": tag_key,
                "Value": tag_value
            }]
        )

    @service_exception_handler
    @resource_exception_handler
    def create_tags_batch(
            self,
            resource_id: str,
            tags_list: Sequence[TagTypeDef]):
        self.logger.debug(f"Tagging resource id {resource_id} with list of tags {tags_list}")
        self.ec2_client.create_tags(Resources=[resource_id], Tags=tags_list)
        self.logger.debug(f"Successfully tagged resource id {resource_id} with list of tags {tags_list}")

    @service_exception_handler
    @resource_exception_handler
    def delete_tags(
            self,
            resource_id: str,
            tag_key: str, ) -> None:
        self.ec2_client.delete_tags(
            Resources=[resource_id],
            Tags=[
                {"Key": tag_key},
            ],
        )
