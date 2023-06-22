# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler
from tgw_vpc_attachment.lib.clients.ec2 import EC2
from tgw_vpc_attachment.lib.exceptions import ResourceNotFoundException
from tgw_vpc_attachment.lib.utils.helper import current_time


@mock_sts
@mock_ec2
def test_vpc_describe_resources_throws_vpc_not_found(organizations_setup):
    # ARRANGE
    override_environment_variables()

    # ASSERT
    with pytest.raises(ResourceNotFoundException):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'VPC',
                'FunctionName': 'describe_resources'
            },
            'event': {
                'AWSSpokeAccountId': organizations_setup['dev_account_id'],
                'resources': ['arn:aws:ec2:us-east-1:555555555555:instance/vpc-b188560f']
            }
        }, LambdaContext())


@mock_sts
@mock_ec2
def test_vpc_describe_resources_throws_subnet_not_found(organizations_setup):
    # ARRANGE
    override_environment_variables()

    # ASSERT
    with pytest.raises(ResourceNotFoundException):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'VPC',
                'FunctionName': 'describe_resources'
            },
            'event': {
                'account': organizations_setup['dev_account_id'],
                'resources': ['arn:aws:ec2:us-east-1:555555555555:instance/subnet-b188560f']
            }
        }, LambdaContext())


@mock_sts
@mock_ec2
def test_vpc_describe_resources_throws_neither_vpc_nor_subnet(organizations_setup):
    # ARRANGE
    override_environment_variables()

    # ASSERT
    with pytest.raises(TypeError):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'VPC',
                'FunctionName': 'describe_resources'
            },
            'event': {
                'account': organizations_setup['dev_account_id'],
                'resources': ['arn:aws:ec2:us-east-1:555555555555:instance/ec2-b188560f']
            }
        }, LambdaContext())


@mock_sts
def test_vpc_describe_resources_vpc(organizations_setup, vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'describe_resources'
        },
        'event': {
            'AWSSpokeAccountId': DEFAULT_ACCOUNT_ID,
            'resources': ['arn:aws:ec2:us-east-1:555555555555:vpc/' + vpc_setup_with_explicit_route_table['vpc_id']]
        }
    }, LambdaContext())

    # ASSERT
    assert response['VpcCidr'] == '10.0.0.0/24'  # from vpc_setup
    assert response['VpcTagFound'] == 'no'


@mock_sts
def test_vpc_describe_resources_vpc_tagged(organizations_setup, vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    ec2_client = EC2()
    ec2_client.create_tags(vpc_setup_with_explicit_route_table['vpc_id'], os.getenv('ASSOCIATION_TAG'), '')

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'describe_resources'
        },
        'event': {
            'AWSSpokeAccountId': DEFAULT_ACCOUNT_ID,
            'resources': ['arn:aws:ec2:us-east-1:555555555555:vpc/' + vpc_setup_with_explicit_route_table['vpc_id']],
            'detail': {'tags': [{'Key': 'Propagate-to', 'Value': ''}]},
        }
    }, LambdaContext())

    # ASSERT
    assert response['VpcCidr'] == '10.0.0.0/24'  # from vpc_setup
    assert response['VpcTagFound'] == 'yes'


@mock_sts
def test_vpc_describe_resources_subnet_no_tag(organizations_setup, vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    # ASSERT
    # Raising an exception is probably not the originally intended behavior of the code,
    # but the observed behavior at the time this test is written.
    # The test captures the observed behavior, since it was not reported as bug so far.
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'VPC',
                'FunctionName': 'describe_resources'
            },
            'event': {
                'AWSSpokeAccountId': DEFAULT_ACCOUNT_ID,
                'resources': ['arn:aws:ec2:us-east-1:555555555555:subnet/' + vpc_setup_with_explicit_route_table['subnet_id']],
                'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
                'detail': {'tags': [{'Key': 'Propagate-to', 'Value': ''}]},
            }
        }, LambdaContext())


@mock_sts
def test_vpc_describe_resources_subnet_tagged(organizations_setup, vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    ec2_client = EC2()
    ec2_client.create_tags(vpc_setup_with_explicit_route_table['subnet_id'], os.getenv('ATTACHMENT_TAG'), '')

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'describe_resources'
        },
        'event': {
            'AWSSpokeAccountId': DEFAULT_ACCOUNT_ID,
            'resources': ['arn:aws:ec2:us-east-1:555555555555:subnet/' + vpc_setup_with_explicit_route_table['subnet_id']],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'detail': {'tags': [{'Key': 'Propagate-to', 'Value': ''}]},
            'time': current_time()
        }
    }, LambdaContext())

    # ASSERT
    assert response['SubnetTagFound'] == 'yes'


@mock_sts
def test_vpc_describe_resources_console_event(organizations_setup, vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()

    ec2_client = EC2()
    ec2_client.create_tags(vpc_setup_with_explicit_route_table['subnet_id'], os.getenv('ATTACHMENT_TAG'), '')

    # ACT
    response = lambda_handler({
        'params': {
            'ClassName': 'VPC',
            'FunctionName': 'describe_resources'
        },
        'event': {
            'AWSSpokeAccountId': DEFAULT_ACCOUNT_ID,
            'AdminAction': 'true',
            'VpcId': vpc_setup_with_explicit_route_table['vpc_id'],
            'SubnetId': vpc_setup_with_explicit_route_table['subnet_id'],
            'TagEventSource': 'subnet',
            'detail': {
                'changed-tag-keys': []
            }
        }
    }, LambdaContext())

    # ASSERT
    assert response['SubnetTagFound'] == 'yes'
