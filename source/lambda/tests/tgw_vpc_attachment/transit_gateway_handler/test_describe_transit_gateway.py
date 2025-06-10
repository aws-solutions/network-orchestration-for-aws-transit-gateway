# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

import boto3
import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_ec2

from tests.tgw_vpc_attachment.conftest import override_environment_variables
from solution.tgw_vpc_attachment.main import lambda_handler


@mock_sts
def test_tgw_describe_transit_gateway_vpc_attachments_existing(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': 'subnet_not_in_attachment_id'
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['FoundExistingSubnetInAttachment'] == 'no'

@mock_sts
def test_tgw_describe_transit_gateway_vpc_attachments_existing_with_subnet(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id']
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['FoundExistingSubnetInAttachment'] == 'yes'


@mock_sts
def test_tgw_describe_transit_gateway_no_vpc_attachment(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': 'vpc_not_attached_with_tgw_id',
            'SubnetIds': vpc_setup_with_explicit_route_table['subnet_id']
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'no'
    assert response['AttachmentState'] == 'deleted'


@mock_sts
def test_describe_transit_gateway_route_tables_with_duplicate_names(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    with mock_ec2():
        ec2_client = boto3.client("ec2", region_name="us-east-1")

    tags = [
        {
            'ResourceType': 'transit-gateway-route-table',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'my-duplicate-route-table-name'
                },
                {
                    'Key': os.environ['APPROVAL_KEY'],
                    'Value': 'No'
                }
            ]
        },
    ]
    ec2_client.create_transit_gateway_route_table(
        TransitGatewayId=vpc_setup_with_explicit_route_table['tgw_id'],
        TagSpecifications=tags
    )

    # create a second route table with same 'name' tag
    ec2_client.create_transit_gateway_route_table(
        TransitGatewayId=vpc_setup_with_explicit_route_table['tgw_id'],
        TagSpecifications=tags
    )

    # ACT
    with pytest.raises(Exception) as error_info:
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'describe_transit_gateway_route_tables'
            },
            'event': {
                'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
                'SubnetId': 'subnet_not_in_attachment_id'
            }}, LambdaContext())

    # ASSERT
    assert "Invalid TGW route table setup. Multiple route tables are tagged with the name my-duplicate-route-table-name, which prevents deterministic TGW association. Please tag each route table with a unique name." in str(
        error_info.value)
