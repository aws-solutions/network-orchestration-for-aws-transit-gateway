# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_ec2
from mypy_boto3_ec2 import EC2Client

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


@mock_sts
@mock_ec2
def test_vpc_default_route_crud_operations_no_route_table():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': {
            'SubnetId': 'subnet-b188560f'
        }}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == 'subnet-b188560f'


@mock_sts
def test_vpc_default_route_crud_operations_all_traffic(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'All-Traffic'

    event = {
        'SubnetId': vpc_setup['subnet_id'],
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
    assert response['SubnetId'] == vpc_setup['subnet_id']


@mock_sts
def test_vpc_default_route_crud_operations_rfc_1918_no_existing_routes(vpc_setup, ec2_client):
    # ARRANGE
    override_environment_variables()
    os.environ['RFC_1918_ROUTES'] = '10.0.12.0/24,pl-10.0.13.0/24'
    os.environ['DEFAULT_ROUTE'] = 'RFC-1918'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': {
            'SubnetId': vpc_setup['subnet_id'],
            'account': '123456789012',
            'region': 'us-east-1',
            'Action': 'AddSubnet',
            'RouteTableId': vpc_setup['route_table_id'],
        }}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup['subnet_id']


@mock_sts
def test_vpc_default_route_crud_operations_rfc_1918(vpc_setup, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['RFC_1918_ROUTES'] = '10.0.12.0/24,10.0.13.0/24,10.0.14.0/24,10.0.15.0/24,10.0.16.0/24'
    os.environ['DEFAULT_ROUTE'] = 'RFC-1918'

    ec2_client.create_route(
        RouteTableId=vpc_setup['route_table_id'],
        DestinationCidrBlock='10.0.12.0/24',
        TransitGatewayId=vpc_setup['tgw_id']
    )
    nat_gateway = ec2_client.create_nat_gateway(SubnetId=vpc_setup['subnet_id'])
    ec2_client.create_route(
        RouteTableId=vpc_setup['route_table_id'],
        DestinationCidrBlock='10.0.13.0/24',
        NatGatewayId=nat_gateway['NatGateway']['NatGatewayId']
    )
    vpc_peering_connection = ec2_client.create_vpc_peering_connection(
        VpcId=vpc_setup['vpc_id'],
        PeerVpcId=vpc_setup['vpc_id']
    )
    ec2_client.create_route(
        RouteTableId=vpc_setup['route_table_id'],
        DestinationCidrBlock='10.0.14.0/24',
        VpcPeeringConnectionId=vpc_peering_connection['VpcPeeringConnection']['VpcPeeringConnectionId']
    )
    gateway = ec2_client.create_internet_gateway()
    ec2_client.create_route(
        RouteTableId=vpc_setup['route_table_id'],
        DestinationCidrBlock='10.0.15.0/24',
        GatewayId=gateway['InternetGateway']['InternetGatewayId']
    )
    ec2_client.create_route(
        RouteTableId=vpc_setup['route_table_id'],
        DestinationCidrBlock='10.0.16.0/24',
    )

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': {
            'SubnetId': vpc_setup['subnet_id'],
            'account': '123456789012',
            'region': 'us-east-1',
            'Action': 'RemoveSubnet',
        }}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup['subnet_id']


@mock_sts
def test_vpc_default_route_crud_operations_custom_destinations(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'

    event = {
        'SubnetId': vpc_setup['subnet_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'AddSubnet',
        'RouteTableId': vpc_setup['route_table_id']
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup['subnet_id']

@mock_sts
def test_vpc_default_route_crud_operations_multiple_cidr_custom_destinations(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'
    os.environ['CIDR_BLOCKS'] = '10.0.0.0/26, 10.0.1.0/26'

    event = {
        'SubnetId': vpc_setup['subnet_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'AddSubnet',
        'RouteTableId': vpc_setup['route_table_id']
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup['subnet_id']

@mock_sts
def test_vpc_default_route_crud_operations_multiple_pls_custom_destinations(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Custom-Destinations'
    os.environ['PREFIX_LISTS'] = 'pl-11111, pl-22222'

    event = {
        'SubnetId': vpc_setup['subnet_id'],
        'account': '123456789012',
        'region': 'us-east-1',
        'Action': 'AddSubnet',
        'RouteTableId': vpc_setup['route_table_id']
    }

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'default_route_crud_operations'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['SubnetId'] == vpc_setup['subnet_id']

@mock_sts
def test_vpc_default_route_crud_operations_configure_manually(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['DEFAULT_ROUTE'] = 'Configure-Manually'

    event = {
        'SubnetId': vpc_setup['subnet_id'],
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
    assert response['SubnetId'] == vpc_setup['subnet_id']
