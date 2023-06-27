# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource lambda"""
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_typing import events
from os import environ
from custom_resource.lib.custom_resource_helper import cfn_handler, start_state_machine

logger = Logger(level=os.getenv('LOG_LEVEL'), service="CUSTOM_RESOURCE")


def lambda_handler(event: events.CloudFormationCustomResourceEvent, context: LambdaContext):
    logger.info("Entering custom resource lambda_handler")
    logger.info(event)
    partition = environ.get("PARTITION")
    if event.get("source") in ["aws.tag", "aws.ec2"]:
        start_state_machine(event, context)

    elif event.get("data") is not None:
        start_state_machine(event.get("data"), context)

    elif event.get("StackId") is not None and f"arn:{partition}:cloudformation" in event.get("StackId"):
        cfn_handler(event, context)

    else:
        raise TypeError("The event is from unknown source type")
