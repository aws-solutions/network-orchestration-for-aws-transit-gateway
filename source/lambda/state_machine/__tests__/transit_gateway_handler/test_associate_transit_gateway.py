import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


@mock_sts
def test_associate_transit_gateway_route_table(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'AttachmentState': 'available',
            'AssociationRouteTableId': vpc_setup['transit_gateway_route_table'],
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AssociationState'] == 'associated'


@mock_sts
def test_associate_transit_gateway_no_route_table(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'AttachmentState': 'available',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response.get('AssociationState') == None


@mock_sts
def test_associate_transit_gateway_rejected(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup['vpc_id'],
            'AttachmentState': 'rejected',
            'AssociationRouteTableId': vpc_setup['transit_gateway_route_table'],
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response.get('AssociationState') == None
