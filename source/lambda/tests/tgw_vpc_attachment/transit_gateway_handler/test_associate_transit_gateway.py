# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from tests.tgw_vpc_attachment.conftest import override_environment_variables
from solution.tgw_vpc_attachment.main import lambda_handler


@mock_sts
def test_associate_transit_gateway_route_table(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'AttachmentState': 'available',
            'AssociationRouteTableId': vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response['AssociationState'] == 'associated'


@mock_sts
def test_associate_transit_gateway_no_route_table(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'AttachmentState': 'available',
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response.get('AssociationState') is None


@mock_sts
def test_associate_transit_gateway_rejected(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']
    os.environ['WAIT_TIME'] = '0'

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'associate_transit_gateway_route_table'
        },
        'event': {
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'AttachmentState': 'rejected',
            'AssociationRouteTableId': vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
            'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment']
        }}, LambdaContext())

    # ASSERT
    assert response.get('AssociationState') is None
