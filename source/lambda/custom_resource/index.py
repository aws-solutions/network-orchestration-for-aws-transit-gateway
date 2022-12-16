# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource lambda"""
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_typing import events

from custom_resource.lib.custom_resource_helper import cfn_handler, start_state_machine

logger = Logger(os.getenv('LOG_LEVEL'))


def lambda_handler(event: events.CloudFormationCustomResourceEvent, context: LambdaContext):
    logger.info("Entering custom resource lambda_handler")
    logger.debug(event)

    if event.get("source") == "aws.tag" or event.get("source") == "aws.ec2":
        start_state_machine(event, context)

    elif event.get("data") is not None:
        start_state_machine(event.get("data"), context)

    elif event.get(
        "StackId"
    ) is not None and "arn:aws:cloudformation" in event.get("StackId"):
        cfn_handler(event, context)

    else:
        raise TypeError("The event is from unknown source type")
