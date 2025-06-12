# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Step Functions test module"""

from moto import mock_stepfunctions
import pytest
from solution.custom_resource.lib.step_functions import StepFunctions

# pylint: disable=too-few-public-methods
@mock_stepfunctions
@pytest.mark.TDD
class TestClassTriggerMachine:
    """TDD test class for Step Functions start_execution calls"""

    name = "my-step-function"
    arn = f"arn:aws:states:us-east-1:111122223333:stateMachine:{name}"

    def test__fail__state_machine_doesnotexist(self):
        """fail with StateMachineDoesNotExist"""
        sfn = StepFunctions()
        with pytest.raises(
            sfn.state_machine_client.exceptions.StateMachineDoesNotExist
        ):
            sfn.trigger_state_machine(
                state_machine_arn=self.arn, sf_input={}, name=self.name
            )
