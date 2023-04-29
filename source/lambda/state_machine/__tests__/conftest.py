#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Setting up pytest fixtures"""

import os

import boto3
import pytest
from moto import mock_organizations, mock_sts, mock_ec2, mock_dynamodb
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ec2.type_defs import VpcTypeDef, SubnetTypeDef, TransitGatewayTypeDef, RouteTableTypeDef, \
    TransitGatewayVpcAttachmentTypeDef, TransitGatewayRouteTableTypeDef

os.environ['USER_AGENT_STRING'] = 'something'
TABLE_NAME = 'stno_table'


def override_environment_variables():
    # override env variables, to avoid accidentally use real credentials on a developer's machine
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["LOG_LEVEL"] = "debug"
    os.environ['TABLE_NAME'] = TABLE_NAME
    os.environ['TTL'] = '90'
    os.environ['CIDR_BLOCKS'] = '10.0.0.0/26'
    os.environ['PREFIX_LISTS'] = 'pl-11111'
    os.environ['ASSOCIATION_TAG'] = 'Associate-with'
    os.environ['ATTACHMENT_TAG'] = 'Attach-to'
    os.environ['PROPAGATION_TAG'] = 'Propagate-to'
    os.environ['LOG_GROUP_ACTIONS'] = 'Actions'
    os.environ['LOG_GROUP_FAILURES'] = 'Failures'


@pytest.fixture(scope="module", autouse=True)
def aws_credentials():
    override_environment_variables()


@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_dynamodb():
        dynamodb_client_resource: DynamoDBServiceResource = boto3.resource("dynamodb")
        table = dynamodb_client_resource.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "SubnetId", "KeyType": "HASH"},
                       {"AttributeName": "Version", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": "SubnetId", "AttributeType": "S"},
                {"AttributeName": "Version", "AttributeType": "S"}, ],
            ProvisionedThroughput={"ReadCapacityUnits": 5,
                                   "WriteCapacityUnits": 5}, )
        table.wait_until_exists()
        os.environ['TABLE_NAME'] = table.table_name
        yield table


@pytest.fixture
def sts_client(aws_credentials):
    with mock_sts():
        connection = boto3.client("sts", region_name="us-east-1")
        yield connection


@pytest.fixture
def org_client(aws_credentials):
    with mock_organizations():
        connection = boto3.client("organizations", region_name="us-east-1")
        yield connection


@pytest.fixture
def organizations_setup(org_client):
    dev_map = {
        "AccountName": "Developer1",
        "AccountEmail": "dev@mock",
        "OUName": "Dev"
    }
    dev_map_2 = {
        "AccountName": "Developer1-SuperSet",
        "AccountEmail": "dev-2@mock",
        "OUName": "Dev"
    }
    prod_map = {
        "AccountName": "Production1",
        "AccountEmail": "prod@mock",
        "OUName": "Prod"
    }

    test_map = {
        "AccountName": "Testing1",
        "AccountEmail": "test@mock",
        "OUName": "Test"
    }
    # create organization
    org_client.create_organization(FeatureSet="ALL")
    root_id = org_client.list_roots()["Roots"][0]["Id"]

    # create accounts
    dev_account_id = org_client.create_account(
        AccountName=dev_map['AccountName'],
        Email=dev_map['AccountEmail'])["CreateAccountStatus"]["AccountId"]
    dev_account_id_2 = org_client.create_account(
        AccountName=dev_map_2['AccountName'],
        Email=dev_map_2['AccountEmail'])["CreateAccountStatus"]["AccountId"]
    test_account_id = org_client.create_account(
        AccountName=test_map['AccountName'],
        Email=test_map['AccountEmail'])["CreateAccountStatus"]["AccountId"]
    prod_account_id = org_client.create_account(
        AccountName=prod_map['AccountName'],
        Email=prod_map['AccountEmail'])["CreateAccountStatus"]["AccountId"]

    # create org units
    dev_resp = org_client.create_organizational_unit(ParentId=root_id,
                                                     Name=dev_map['OUName'])
    dev_ou_id = dev_resp["OrganizationalUnit"]["Id"]
    test_resp = org_client.create_organizational_unit(ParentId=root_id,
                                                      Name=test_map['OUName'])
    test_ou_id = test_resp["OrganizationalUnit"]["Id"]
    prod_resp = org_client.create_organizational_unit(ParentId=root_id,
                                                      Name=prod_map['OUName'])
    prod_ou_id = prod_resp["OrganizationalUnit"]["Id"]

    # move accounts
    org_client.move_account(
        AccountId=dev_account_id, SourceParentId=root_id,
        DestinationParentId=dev_ou_id
    )
    org_client.move_account(
        AccountId=dev_account_id_2, SourceParentId=root_id,
        DestinationParentId=dev_ou_id
    )
    org_client.move_account(
        AccountId=test_account_id, SourceParentId=root_id,
        DestinationParentId=test_ou_id
    )
    org_client.move_account(
        AccountId=prod_account_id, SourceParentId=root_id,
        DestinationParentId=prod_ou_id
    )
    yield {
        'dev_account_id': dev_account_id,
        'dev_account_id_2': dev_account_id_2,
        'test_account_id': test_account_id,
        'prod_account_id': prod_account_id,
        'dev_ou_id': dev_ou_id
    }


@pytest.fixture
def ec2_client(aws_credentials):
    with mock_ec2():
        connection = boto3.client("ec2", region_name="us-east-1")
        yield connection


@pytest.fixture
def vpc_setup(ec2_client: EC2Client):
    transit_gateway: TransitGatewayTypeDef = ec2_client.create_transit_gateway()['TransitGateway']
    os.environ["TGW_ID"] = transit_gateway['TransitGatewayId']

    vpc: VpcTypeDef = ec2_client.create_vpc(
        CidrBlock='10.0.0.0/24'
    )['Vpc']
    subnet: SubnetTypeDef = ec2_client.create_subnet(
        CidrBlock='10.0.0.0/28',
        VpcId=vpc['VpcId']
    )['Subnet']
    tgw_vpc_attachment: TransitGatewayVpcAttachmentTypeDef = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=transit_gateway['TransitGatewayId'],
        VpcId=vpc['VpcId'],
        SubnetIds=[subnet['SubnetId']]
    )['TransitGatewayVpcAttachment']
    route_table: RouteTableTypeDef = ec2_client.create_route_table(
        VpcId=vpc['VpcId']
    )['RouteTable']
    gateway_route_table: TransitGatewayRouteTableTypeDef = ec2_client.create_transit_gateway_route_table(
        TransitGatewayId=transit_gateway['TransitGatewayId']
    )['TransitGatewayRouteTable']
    ec2_client.associate_route_table(
        RouteTableId=(route_table['RouteTableId']),
        SubnetId=subnet['SubnetId']
    )
    tgw_route_table_association = ec2_client.associate_route_table(
        RouteTableId=(gateway_route_table['TransitGatewayRouteTableId']),
        SubnetId=subnet['SubnetId']
    )

    yield {
        'tgw_id': transit_gateway['TransitGatewayId'],
        'vpc_id': vpc['VpcId'],
        'subnet_id': subnet['SubnetId'],
        'tgw_vpc_attachment': tgw_vpc_attachment['TransitGatewayAttachmentId'],
        'route_table_id': route_table['RouteTableId'],
        'transit_gateway_route_table': gateway_route_table['TransitGatewayRouteTableId'],
        'tgw_route_table_association': tgw_route_table_association['AssociationId'],
    }
