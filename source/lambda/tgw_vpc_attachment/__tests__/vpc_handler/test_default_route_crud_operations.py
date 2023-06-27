# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_ec2
from mypy_boto3_ec2 import EC2Client

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler
from tgw_vpc_attachment.lib.clients.ec2 import EC2
from botocore.exceptions import ClientError


@mock_sts
def test_vpc_default_create_main_route(vpc_setup_no_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'
    EC2().create_tags(
        vpc_setup_no_explicit_route_table['subnet_id'],
        os.environ['ATTACHMENT_TAG'],
        'main-route-table-only'
    )

    event = {
        'SubnetId': vpc_setup_no_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_no_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'MainRouteTableOnly': 'yes',
        'Action': 'CreateTgwVpcAttachment'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'
    assert response['RouteTableType'] == "Main"


@mock_sts
def test_vpc_default_delete_main_route(vpc_setup_no_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'
    EC2().create_tags(
        vpc_setup_no_explicit_route_table['subnet_id'],
        os.environ['ATTACHMENT_TAG'],
        'main-route-table-only'
    )
    event = {
        'SubnetId': vpc_setup_no_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_no_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'MainRouteTableOnly': 'no',
        'Action': 'DeleteTgwVpcAttachment'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # This assertion is due to destination prefix not matching with Destination cidr block
    # ASSERT
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'
    assert response['RouteTableType'] == "Main"


@mock_sts
@mock_ec2
def test_vpc_default_route_crud_operations_no_route_table(vpc_setup_no_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    # ACT
    with pytest.raises(IndexError):
        lambda_handler({
            'params': {
                'ClassName': 'VPC',
                'FunctionName': 'default_route_crud_operations',

            },
            'event': {
                'SubnetId': vpc_setup_no_explicit_route_table['subnet_id'],
                'VpcId': vpc_setup_no_explicit_route_table['vpc_id'],
                'account': '123456789012'
            }}, LambdaContext())


@mock_sts
def test_vpc_default_create_route_to_tgw_tag(vpc_setup_with_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['subnet_id'],
        os.environ['ROUTING_TAG'],
        ''
    )
    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'MainRouteTableOnly': 'yes',
        'Action': 'CreateTgwVpcAttachment'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'
    assert response['RouteTableType'] == "Explicit"

@mock_sts
def test_vpc_default_delete_route_to_tgw_tag(vpc_setup_with_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['subnet_id'],
        os.environ['ROUTING_TAG'],
        ''
    )
    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'DeleteTgwVpcAttachment'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'
    assert response['RouteTableType'] == "Explicit"




@mock_sts
def test_default_route_crud_operations_all_traffic_for_main_route_table(vpc_setup_no_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'
    EC2().create_tags(
        vpc_setup_no_explicit_route_table['subnet_id'],
        os.environ['ATTACHMENT_TAG'],
        'main-route-table-only'
    )
    event = {
        'SubnetId': vpc_setup_no_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_no_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'MainRouteTableOnly': 'yes',
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['RouteTableId'] == vpc_setup_no_explicit_route_table['main_route_table_id']
    assert response['RouteTableType'] == 'Main'
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'


@mock_sts
def test_vpc_default_route_crud_operations_all_traffic(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'

    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['RouteTableId'] == vpc_setup_with_explicit_route_table['route_table_id']
    assert response['RouteTableType'] == 'Explicit'
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'


@mock_sts
def test_vpc_default_route_crud_operations_rfc_1918_no_existing_routes(vpc_setup_with_explicit_route_table, ec2_client):
    # ARRANGE
    override_environment_variables()
    os.environ['RFC_1918_ROUTES'] = '10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16'
    os.environ['DEFAULT_ROUTE'] = 'RFC-1918'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': {
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'account': '123456789012',
            'region': 'us-east-1',
            'Action': 'AddSubnet',
            'RouteTableId': vpc_setup_with_explicit_route_table['route_table_id'],
        }}, LambdaContext())

    # ASSERT
    assert response['RouteTableId'] == vpc_setup_with_explicit_route_table['route_table_id']
    assert response['RouteTableType'] == 'Explicit'
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'


@mock_sts
def test_vpc_default_route_crud_operations_rfc_1918(vpc_setup_with_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['RFC_1918_ROUTES'] = '10.0.12.0/24,10.0.13.0/24,10.0.14.0/24,10.0.15.0/24,10.0.16.0/24'
    os.environ['DEFAULT_ROUTE'] = 'RFC-1918'

    ec2_client.create_route(
        RouteTableId=vpc_setup_with_explicit_route_table['route_table_id'],
        DestinationCidrBlock='10.0.12.0/24',
        TransitGatewayId=vpc_setup_with_explicit_route_table['tgw_id']
    )
    nat_gateway = ec2_client.create_nat_gateway(SubnetId=vpc_setup_with_explicit_route_table['subnet_id'])
    ec2_client.create_route(
        RouteTableId=vpc_setup_with_explicit_route_table['route_table_id'],
        DestinationCidrBlock='10.0.13.0/24',
        NatGatewayId=nat_gateway['NatGateway']['NatGatewayId']
    )
    vpc_peering_connection = ec2_client.create_vpc_peering_connection(
        VpcId=vpc_setup_with_explicit_route_table['vpc_id'],
        PeerVpcId=vpc_setup_with_explicit_route_table['vpc_id']
    )
    ec2_client.create_route(
        RouteTableId=vpc_setup_with_explicit_route_table['route_table_id'],
        DestinationCidrBlock='10.0.14.0/24',
        VpcPeeringConnectionId=vpc_peering_connection['VpcPeeringConnection']['VpcPeeringConnectionId']
    )
    gateway = ec2_client.create_internet_gateway()
    ec2_client.create_route(
        RouteTableId=vpc_setup_with_explicit_route_table['route_table_id'],
        DestinationCidrBlock='10.0.15.0/24',
        GatewayId=gateway['InternetGateway']['InternetGatewayId']
    )
    ec2_client.create_route(
        RouteTableId=vpc_setup_with_explicit_route_table['route_table_id'],
        DestinationCidrBlock='10.0.16.0/24',
    )

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': {
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'account': '123456789012',
            'region': 'us-east-1',
            'Action': 'RemoveSubnet',
        }}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup_with_explicit_route_table['subnet_id']
    assert response['RouteTableType'] == 'Explicit'
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'yes'


@mock_sts
def test_vpc_default_route_crud_operations_custom_destinations_prefix_list(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'
    os.environ['CIDR_BLOCKS'] = ''
    os.environ['PREFIX_LISTS'] = 'pl-1ab2cd, pl-s9d8f7'

    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations',

        },
        'event': {
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'account': '123456789012',
            'Action': 'AddSubnet'
        }}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup_with_explicit_route_table['subnet_id']
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'
    assert response['GatewayId'] is None


@mock_sts
def test_vpc_default_route_crud_operations_custom_destinations_invalid_cidr_block(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'
    os.environ['CIDR_BLOCKS'] = '10.0.0.0/23'
    os.environ["PREFIX_LISTS"] = ''

    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'AddSubnet'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['RouteTableId'] == vpc_setup_with_explicit_route_table['route_table_id']
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'


@mock_sts
def test_vpc_default_route_crud_operations_custom_destinations(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'
    os.environ['CIDR_BLOCKS'] = '10.0.0.0/26'
    os.environ["PREFIX_LISTS"] = ''

    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'AddSubnet'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup_with_explicit_route_table['subnet_id']
    assert response['DefaultRouteToTgwExists'] == 'no'
    assert response['DestinationRouteExists'] == 'no'


@mock_sts
def test_vpc_default_route_crud_operations_configure_manually(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Configure-Manually'

    event = {
        'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
        'account': '123456789012',
        'region': 'us-east-1'
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup_with_explicit_route_table['subnet_id']
    assert response['RouteTableType'] == 'Explicit'
