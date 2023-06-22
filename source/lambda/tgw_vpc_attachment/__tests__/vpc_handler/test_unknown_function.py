# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts
from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler


@mock_sts
def test_vpc_function_not_found():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler(
        {'params': {
            'ClassName': 'VPC',
            'FunctionName': 'foo'
        }}, LambdaContext())

    # ASSERT
    assert response['Message'] == "Function name does not match any function in the handler file."
