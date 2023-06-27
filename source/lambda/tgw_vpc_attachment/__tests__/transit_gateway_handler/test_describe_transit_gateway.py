import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler


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
