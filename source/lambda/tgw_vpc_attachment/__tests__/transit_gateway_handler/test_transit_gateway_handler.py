import os

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_ec2
from mypy_boto3_ec2 import EC2Client

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.lib.clients.ec2 import EC2
from tgw_vpc_attachment.lib.exceptions import ResourceBusyException
from tgw_vpc_attachment.main import lambda_handler
from tgw_vpc_attachment.lib.handlers.tgw_vpc_attachment_handler import TransitGatewayVPCAttachments

from unittest.mock import patch


@mock_sts
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
def test_disassociate_transit_gateway_route_table_raises(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

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
                'ExistingAssociationRouteTableId': vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
                'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
            }}, LambdaContext())


@mock_sts
def test_disassociate_transit_gateway_route_table(vpc_setup_with_explicit_route_table, ec2_client: EC2Client):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    association = ec2_client.associate_transit_gateway_route_table(
        TransitGatewayRouteTableId=vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        TransitGatewayAttachmentId=vpc_setup_with_explicit_route_table['tgw_vpc_attachment'])

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
@patch('tgw_vpc_attachment.lib.clients.ec2.EC2.get_transit_gateway_route_table_associations')
def test_get_association_state(mock_get_tgw_rtb_associations, vpc_setup_with_explicit_route_table):
    tgw_attachments = TransitGatewayVPCAttachments(vpc_setup_with_explicit_route_table)

    # disassociated state, returns empty list
    mock_get_tgw_rtb_associations.return_value = []
    assert tgw_attachments._get_association_state('myTable') == 'disassociated'

    # state transition from associating -> associated
    mock_get_tgw_rtb_associations.side_effect = [[{'State': 'associating'}], [{'State': 'associated'}]]
    os.environ["WAIT_TIME"] = '1'
    assert tgw_attachments._get_association_state('myTable') == 'associated'


@mock_sts
@patch('tgw_vpc_attachment.lib.clients.ec2.EC2.get_transit_gateway_route_table_associations')
def test_get_association_state_raises_exception(mock_get_tgw_rtb_associations, vpc_setup_with_explicit_route_table):
    tgw_attachments = TransitGatewayVPCAttachments(vpc_setup_with_explicit_route_table)

    # first incorrect state, then stuck in associating. 3 return values to match call count.
    mock_get_tgw_rtb_associations.side_effect = [
        {'Error': 'IncorrectState'},
        [{'State': 'associating'}],
        [{'State': 'associating'}]
    ]
    os.environ["WAIT_TIME"] = '1'
    os.environ["MAX_RETRY"] = '3'

    with pytest.raises(ResourceBusyException):
        tgw_attachments._get_association_state('myTable')

    assert mock_get_tgw_rtb_associations.call_count == int(os.environ["MAX_RETRY"])

@mock_sts
def test_get_transit_gateway_attachment_propagations(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    with pytest.raises(Exception):
        lambda_handler({
            'params': {
                'ClassName': 'TransitGateway',
                'FunctionName': 'get_transit_gateway_attachment_propagations'
            },
            'event': {
                'AttachmentState': 'available',
                'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
            }}, LambdaContext())

    # throws exception because not implemented in moto


@mock_sts
def test_get_transit_gateway_attachment_propagations_rejected(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'get_transit_gateway_attachment_propagations'
        },
        'event': {
            'AttachmentState': 'rejected',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'rejected'


@mock_sts
def test_enable_transit_gateway_route_table_propagation_skip(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'enable_transit_gateway_route_table_propagation'
        },
        'event': {
            'AttachmentState': 'available',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
            'PropagationRouteTableIds': []
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
@mock_ec2
@patch('tgw_vpc_attachment.lib.clients.ec2.EC2.enable_transit_gateway_route_table_propagation')
@patch.object(TransitGatewayVPCAttachments, '_get_propagation_route_tables_to_enable')
def test_enable_transit_gateway_route_table_propagation_raises_exception(
        mock_get_propagation_rtb, mock_enable_propagation, vpc_setup_with_explicit_route_table):

    # ARRANGE
    vpc_setup_with_explicit_route_table['AttachmentState'] = "available"
    mock_get_propagation_rtb.return_value = ['rtb-0000']
    mock_enable_propagation.return_value = ({'Error': 'IncorrectState'})

    # ACT
    tgw_attachments = TransitGatewayVPCAttachments(vpc_setup_with_explicit_route_table)

    # ASSERT
    with pytest.raises(ResourceBusyException):
        tgw_attachments.enable_transit_gateway_route_table_propagation()


@mock_sts
def test_enable_transit_gateway_route_table_propagation(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'enable_transit_gateway_route_table_propagation'
        },
        'event': {
            'AttachmentState': 'available',
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
            'PropagationRouteTableIds': [vpc_setup_with_explicit_route_table['transit_gateway_route_table']]
        }}, LambdaContext())

    # ASSERT
    assert response['EnablePropagationRouteTableIds'] == [
        vpc_setup_with_explicit_route_table['transit_gateway_route_table']]


@mock_sts
def test_disable_transit_gateway_route_table_propagation_raises(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

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
                'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
                'ExistingPropagationRouteTableIds': [
                    vpc_setup_with_explicit_route_table['transit_gateway_route_table']],
                'PropagationRouteTableIds': []
            }}, LambdaContext())


@mock_sts
def test_get_transit_gateway_vpc_attachment_state(vpc_setup_with_explicit_route_table):
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
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
            'ExistingPropagationRouteTableIds': [vpc_setup_with_explicit_route_table['transit_gateway_route_table']],
            'PropagationRouteTableIds': []
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'available'


@mock_sts
def test_get_transit_gateway_vpc_attachment_state_no_attachment(vpc_setup_with_explicit_route_table):
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
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
            'ExistingPropagationRouteTableIds': [vpc_setup_with_explicit_route_table['transit_gateway_route_table']],
            'PropagationRouteTableIds': [],
            'AttachmentState': 'deleted'  # describe_transit_gateway_vpc_attachments will set it to deleted
        }}, LambdaContext())

    # ASSERT
    assert response['AttachmentState'] == 'deleted'


@mock_sts
def test_tag_transit_gateway_attachment(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    tag_key = "foo"
    tag_value = "bar"

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'tag_transit_gateway_attachment'
        },
        'event': {
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
            'AttachmentTagsRequired': {tag_key: tag_value},
        }}, LambdaContext())

    # ASSERT
    transit_gateway_vpc_attachment = EC2().describe_transit_gateway_vpc_attachments(
        vpc_setup_with_explicit_route_table['tgw_id'],
        vpc_setup_with_explicit_route_table['vpc_id']
    )[0]
    assert transit_gateway_vpc_attachment['Tags'][0]['Key'] == tag_key
    assert transit_gateway_vpc_attachment['Tags'][0]['Value'] == tag_value


@mock_sts
def test_subnet_deletion_event(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'subnet_deletion_event'
        },
        'event': {
            'detail': {
                'requestParameters': {
                    'subnetId': vpc_setup_with_explicit_route_table['subnet_id']
                },
            }
        }
    }, LambdaContext())

    # ASSERT
    assert response == 'Deleted transit gateway VPC attachment ' + vpc_setup_with_explicit_route_table[
        'tgw_vpc_attachment']


@mock_sts
def test_update_spoke_resource_tags_if_failed(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'update_spoke_resource_tags_if_failed'
        },
        'event': {
            'Status': 'failed',
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
        }
    }, LambdaContext())

    # ASSERT
    assert response['Status'] == 'failed'
