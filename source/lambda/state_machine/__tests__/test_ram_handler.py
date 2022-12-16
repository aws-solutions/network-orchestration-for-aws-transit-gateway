# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import List

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts
from mypy_boto3_ram.type_defs import ResourceShareInvitationTypeDef

from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler


def mock_ram(mocker, elements: List[ResourceShareInvitationTypeDef]):
    # patch RAM calls with mocker, since moto has not yet implemented the required operations
    def mock_get_invitations(self, arn) -> List[ResourceShareInvitationTypeDef]:
        return elements

    mocker.patch("state_machine.lib.clients.ram.RAM.get_resource_share_invitations", mock_get_invitations)

    def mock_accept_invitations(self, arn):
        return {}

    mocker.patch("state_machine.lib.clients.ram.RAM.accept_resource_share_invitation", mock_accept_invitations)


def test_ram_function_not_found():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler(
        {'params': {
            'ClassName': 'ResourceAccessManager',
            'FunctionName': 'foo'
        }}, LambdaContext())

    # ASSERT
    assert response['Message'] == "Function name does not match any function in the handler file."


def test_ram_accept_resource_share_invitation_in_org():
    # ARRANGE
    override_environment_variables()

    os.environ['FIRST_PRINCIPAL'] = 'arn:aws:organizations'

    # ACT
    event = {}
    response = lambda_handler({
        'params': {
            'ClassName': 'ResourceAccessManager',
            'FunctionName': 'accept_resource_share_invitation'
        },
        'event': event
    }, LambdaContext())

    # ASSERT the event is returned unmodified
    assert response == event


@mock_sts
def test_ram_accept_resource_share_invitation(mocker):
    # ARRANGE
    override_environment_variables()
    transit_gateway_arn = 'arn:aws:ec2:us-east-1:111122223333:transit-gateway/tgw-01c773291e6197de1'

    pending_invitation: ResourceShareInvitationTypeDef = {
        'senderAccountId': '123456789012',
        'status': 'PENDING',
        'resourceShareArn': transit_gateway_arn
    }
    mock_ram(mocker, [pending_invitation])

    os.environ['FIRST_PRINCIPAL'] = 'nope'
    os.environ['RESOURCE_SHARE_ARN'] = transit_gateway_arn
    event = {}

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'ResourceAccessManager',
            'FunctionName': 'accept_resource_share_invitation'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ResourceShareArnAccepted'] == transit_gateway_arn


@mock_sts
def test_ram_accept_resource_share_invitation_not_pending(mocker):
    # ARRANGE
    override_environment_variables()
    transit_gateway_arn = 'arn:aws:ec2:us-east-1:111122223333:transit-gateway/tgw-01c773291e6197de1'

    rejected_invitation: ResourceShareInvitationTypeDef = {
        'senderAccountId': '123456789012',
        'status': 'REJECTED'
    }
    mock_ram(mocker, [rejected_invitation])

    os.environ['FIRST_PRINCIPAL'] = 'nope'
    os.environ['RESOURCE_SHARE_ARN'] = transit_gateway_arn
    event = {}

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'ResourceAccessManager',
            'FunctionName': 'accept_resource_share_invitation'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ResourceShareArnAccepted'] == None


def test_ram_accept_resource_share_invitation_inside_organization(mocker):
    # ARRANGE
    override_environment_variables()

    os.environ['FIRST_PRINCIPAL'] = 'arn:aws:organizations'
    event = {}

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'ResourceAccessManager',
            'FunctionName': 'accept_resource_share_invitation'
        },
        'event': event
    }, LambdaContext())

    # ASSERT the event is returned unmodified
    assert response == event


@mock_sts
def test_ram_raises_exception_when_RAM_call_fails(mocker):
    # ARRANGE
    override_environment_variables()

    def mock_get_invitations(self, arn) -> List[ResourceShareInvitationTypeDef]:
        raise Exception('Some exception')

    mocker.patch("state_machine.lib.clients.ram.RAM.get_resource_share_invitations", mock_get_invitations)

    os.environ['FIRST_PRINCIPAL'] = 'nope'
    event = {}

    # ASSERT
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'ResourceAccessManager',
                'FunctionName': 'accept_resource_share_invitation'
            },
            'event': event
        }, LambdaContext())
