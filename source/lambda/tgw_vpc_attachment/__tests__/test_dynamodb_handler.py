# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts, mock_dynamodb

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler


def test_dynamodb_function_not_found():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler(
        {'params': {
            'ClassName': 'DynamoDb',
            'FunctionName': 'foo'
        }}, LambdaContext())

    # ASSERT
    assert response['Message'] == "Function name does not match any function in the handler file."


@mock_sts
@mock_dynamodb
def test_dynamodb_throws_table_not_found():
    # ARRANGE
    override_environment_variables()

    # ASSERT
    with pytest.raises(Exception):
        # ACT
        lambda_handler({
            'params': {
                'ClassName': 'DynamoDb',
                'FunctionName': 'put_item'
            },
            'event': {
                'VpcId': 'vpc-b188560f',
                'time': '2022-08-12T18:04:42Z'
            }
        }, LambdaContext())
