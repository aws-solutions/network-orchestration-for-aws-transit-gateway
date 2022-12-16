import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


@mock_sts
def test_tgw_attachment_crud_operations_create(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': vpc_setup['subnet_id'],
            'TgwAttachmentExist': 'no',
            'SubnetTagFound': 'yes'
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['Action'] == 'CreateTgwVpcAttachment'


@mock_sts
def test_tgw_attachment_crud_operations_update(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': vpc_setup['subnet_id'],
            'FoundExistingSubnetInAttachment': 'no',
            'SubnetTagFound': 'yes',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
def test_tgw_attachment_crud_operations_delete(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': vpc_setup['subnet_id'],
            'FoundExistingSubnetInAttachment': 'yes',
            'SubnetTagFound': 'no',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
def test_tgw_attachment_crud_operations_noop(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tgw_attachment_crud_operations'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': vpc_setup['subnet_id'],
            'FoundExistingSubnetInAttachment': 'yes',
            'SubnetTagFound': 'yes',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
