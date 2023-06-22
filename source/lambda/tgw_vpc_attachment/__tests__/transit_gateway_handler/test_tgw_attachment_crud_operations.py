import os

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts
from botocore.exceptions import ClientError
from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler


@mock_sts
def test_tgw_attachment_crud_operations_create(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'TgwAttachmentExist': 'no',
            'SubnetTagFound': 'yes'
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['Action'] == 'CreateTgwVpcAttachment'


@mock_sts
def test_tgw_attachment_crud_operations_update(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'FoundExistingSubnetInAttachment': 'no',
            'SubnetTagFound': 'yes',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'
    assert response['Action'] == 'AddSubnet'


@mock_sts
def test_tgw_attachment_crud_operations_update_auto_reject(vpc_setup_with_explicit_route_table, mocker):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    def mock_add_subnet_to_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ):
        return {"Error": "DuplicateSubnetsInSameZone"}

    mocker.patch(
        "tgw_vpc_attachment.lib.clients.ec2.EC2.add_subnet_to_tgw_attachment",
        mock_add_subnet_to_tgw_attachment
    )

    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'FoundExistingSubnetInAttachment': 'no',
            'SubnetTagFound': 'yes',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['Status'] == 'auto-rejected'
    assert response['Action'] == 'AddSubnet'


@mock_sts
def test_tgw_attachment_crud_operations_remove_subnet(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'FoundExistingSubnetInAttachment': 'yes',
            'SubnetTagFound': 'no',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'
    assert response['Action'] == 'RemoveSubnet'

@mock_sts
def test_tgw_attachment_crud_operations_delete_tgw_attachment(vpc_setup_with_explicit_route_table, mocker):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    def mock_remove_subnet_from_tgw_attachment(
            self,
            tgw_attachment_id: str,
            subnet_id: str
    ):
        return {"Error": "InsufficientSubnetsException"}

    mocker.patch(
        "tgw_vpc_attachment.lib.clients.ec2.EC2.remove_subnet_from_tgw_attachment",
        mock_remove_subnet_from_tgw_attachment
    )

    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'FoundExistingSubnetInAttachment': 'yes',
            'SubnetTagFound': 'no',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    print(response)
    assert response['AttachmentState'] == 'deleted'
    assert response['Action'] == 'DeleteTgwVpcAttachment'


@mock_sts
def test_tgw_attachment_crud_operations_noop(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'FoundExistingSubnetInAttachment': 'yes',
            'SubnetTagFound': 'yes',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
