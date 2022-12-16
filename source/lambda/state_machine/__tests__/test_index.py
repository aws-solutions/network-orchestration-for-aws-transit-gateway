# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_lambda_powertools.utilities.typing import LambdaContext

from state_machine.__tests__.conftest import override_environment_variables


def test_class_not_found():
    # ARRANGE
    override_environment_variables()

    # import after setup, because import causes usages of env variables
    from state_machine.index import lambda_handler

    # ACT
    response = lambda_handler({}, LambdaContext())

    # ASSERT
    assert response["Message"] == "Class name not found in input."


def test_function_not_found():
    # ARRANGE
    override_environment_variables()

    # import after setup, because import causes usages of env variables
    from state_machine.index import lambda_handler

    # ACT
    response = lambda_handler({'params': {'ClassName': 'GeneralFunctions'}}, LambdaContext())

    # ASSERT
    assert response["Message"] == "Function name does not match any function in the handler file."
