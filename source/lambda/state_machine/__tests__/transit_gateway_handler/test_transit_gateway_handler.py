import os

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts
from mypy_boto3_ec2 import EC2Client

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


def test_tgw_function_not_found():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler(
        {'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'foo'
        }}, LambdaContext())

    # ASSERT
    assert response['Message'] == "Function name does not match any function in the handler file."



@mock_sts
def test_describe_transit_gateway_route_tables(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': {
            'RouteTableList': [vpc_setup['route_table_id']],
            'AssociationRouteTableId': 'foo',
            'ExistingAssociationRouteTableId': 'foo',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            os.getenv('ASSOCIATION_TAG'): '',
            os.getenv('PROPAGATION_TAG'): '',
        }}, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'


@mock_sts
def test_disassociate_transit_gateway_route_table_raises(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ASSERT
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'disassociate_transit_gateway_route_table'
            },
            'event': {
                'AttachmentState': 'available',
                'ExistingAssociationRouteTableId': vpc_setup['transit_gateway_route_table'],
                'TransitGatewayAttachmentId': vpc_setup['tgw_route_table_association']
            }}, LambdaContext())


@mock_sts
def test_disassociate_transit_gateway_route_table(vpc_setup, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    association = ec2_client.associate_transit_gateway_route_table(
        TransitGatewayRouteTableId=vpc_setup['transit_gateway_route_table'],
        TransitGatewayAttachmentId=vpc_setup['tgw_vpc_attachment'])

    # ASSERT
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'disassociate_transit_gateway_route_table'
            },
            'event': {
                'AttachmentState': 'available',
                'ExistingAssociationRouteTableId': association['Association']['TransitGatewayRouteTableId'],
                'TransitGatewayAttachmentId': association['Association']['TransitGatewayAttachmentId']
            }}, LambdaContext())

    # throws exception because get_transit_gateway_route_table_associations is not implemented in moto


@mock_sts
def test_get_transit_gateway_attachment_propagations(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    with pytest.raises(Exception):
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'get_transit_gateway_attachment_propagations'
            },
            'event': {
                'AttachmentState': 'available',
                'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
            }}, LambdaContext())

    # throws exception because not implemented in moto


@mock_sts
def test_get_transit_gateway_attachment_propagations_rejected(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'get_transit_gateway_attachment_propagations'
        },
        'event': {
            'AttachmentState': 'rejected',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'rejected'


@mock_sts
def test_enable_transit_gateway_route_table_propagation_skip(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'enable_transit_gateway_route_table_propagation'
        },
        'event': {
            'AttachmentState': 'available',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            'PropagationRouteTableIds': []
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
def test_enable_transit_gateway_route_table_propagation(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'enable_transit_gateway_route_table_propagation'
        },
        'event': {
            'AttachmentState': 'available',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            'PropagationRouteTableIds': [vpc_setup['transit_gateway_route_table']]
        }}, LambdaContext())

    # ASSERT
    assert response['EnablePropagationRouteTableIds'] == [vpc_setup['transit_gateway_route_table']]


@mock_sts
def test_disable_transit_gateway_route_table_propagation_raises(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ASSERT
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'disable_transit_gateway_route_table_propagation'
            },
            'event': {
                'AttachmentState': 'available',
                'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
                'ExistingPropagationRouteTableIds': [vpc_setup['transit_gateway_route_table']],
                'PropagationRouteTableIds': []
            }}, LambdaContext())


@mock_sts
def test_get_transit_gateway_vpc_attachment_state(vpc_setup):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'get_transit_gateway_vpc_attachment_state'
        },
        'event': {
            'TgwAttachmentExist': 'yes',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            'ExistingPropagationRouteTableIds': [vpc_setup['transit_gateway_route_table']],
            'PropagationRouteTableIds': []
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
def test_get_transit_gateway_vpc_attachment_state_no_attachment(vpc_setup):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'get_transit_gateway_vpc_attachment_state'
        },
        'event': {
            'TgwAttachmentExist': 'no',
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            'ExistingPropagationRouteTableIds': [vpc_setup['transit_gateway_route_table']],
            'PropagationRouteTableIds': []
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'deleted'


@mock_sts
def test_tag_transit_gateway_attachment(vpc_setup):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tag_transit_gateway_attachment'
        },
        'event': {
            'TransitGatewayAttachmentId': vpc_setup['tgw_vpc_attachment'],
            'AttachmentTagsRequired': {'foo': 'bar'},
        }}, LambdaContext())

    # ASSERT
    print(response)


@mock_sts
def test_subnet_deletion_event(vpc_setup):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'subnet_deletion_event'
        },
        'event': {
            'detail': {
                'requestParameters': {
                    'subnetId': vpc_setup['subnet_id']
                },
            }
        }
    }, LambdaContext())

    # ASSERT
    assert response == 'Deleted transit gateway VPC attachment ' + vpc_setup['tgw_vpc_attachment']


@mock_sts
def test_update_tags_if_failed(vpc_setup):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'update_tags_if_failed'
        },
        'event': {
            'Status': 'failed',
            'SubnetId': vpc_setup['subnet_id'],
            'VpcId': vpc_setup['vpc_id'],
        }
    }, LambdaContext())

    # ASSERT
    assert response['Status'] == 'failed'
