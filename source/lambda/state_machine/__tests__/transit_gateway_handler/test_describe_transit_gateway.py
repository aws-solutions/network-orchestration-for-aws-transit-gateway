import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


@mock_sts
def test_tgw_describe_transit_gateway_vpc_attachments_existing(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': 'some_id'
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['FoundExistingSubnetInAttachment'] == 'no'


@mock_sts
def test_tgw_describe_transit_gateway_vpc_attachments_existing_with_subnet(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'SubnetId': vpc_setup['subnet_id']
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'yes'
    assert response['FoundExistingSubnetInAttachment'] == 'yes'


@mock_sts
def test_tgw_describe_transit_gateway_no_vpc_attachment(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_vpc_attachments'
        },
        'event': {
            'VpcId': 'other_vpc',
            'SubnetIds': vpc_setup['subnet_id']
        }}, LambdaContext())

    # ASSERT
    assert response['TgwAttachmentExist'] == 'no'
    assert response['AttachmentState'] == 'does-not-exist'
