# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from custom_resource.lib.utils import boto3_config


class StepFunctions:

    def __init__(self):
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.state_machine_client = boto3.client(
            "stepfunctions", config=boto3_config
        )

    def trigger_state_machine(self, state_machine_arn, sf_input, name):
        """Starts a state machine execution

        Args:
            state_machine_arn (string): Amazon Resource Name (ARN) of the state machine to execute
            sf_input (JSON): JSON input data for the execution
            name (string): The name of the execution

        Returns:
            string: api response, Amazon Resource Name (ARN) that identifies the execution

        Raises:
            SFN.Client.exceptions.StateMachineDoesNotExist: thrown when state machine not found
            ClientError: general exception provided by an AWS service to Boto3 client's request
        """
        log_message = {
            "METHOD": "trigger_state_machine",
            "MESSAGE": f"triggering state machine, arn: {state_machine_arn},\
                 input: {sf_input}, name: {name}",
        }
        self.logger.debug(str(log_message))
        try:
            response = self.state_machine_client.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps(sf_input),
                name=name,
            )
            return response.get("executionArn")
        except (
            self.state_machine_client.exceptions.StateMachineDoesNotExist,
            ClientError,
        ) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise
