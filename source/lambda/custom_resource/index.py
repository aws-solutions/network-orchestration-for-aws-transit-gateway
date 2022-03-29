# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource lambda"""

from os import environ
import logging
from custom_resource.lib.custom_resource_helper import cfn_handler, trigger_sm
from custom_resource.lib.utils import setup_logger

setup_logger(environ.get("LOG_LEVEL"))
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """entry point for custom resource microservice

    Args:
        event (dict): lambda triggering event
        context (object): lambda context object to the handler

    Raises:
        Exception: general exception to handle failures

    Returns:
        None
    """

    logger.info("Entering custom resource lambda_handler")
    logger.debug(event)

    if event.get("source") == "aws.tag" or event.get("source") == "aws.ec2":
        trigger_sm(event, context)

    elif event.get("data") is not None:
        trigger_sm(event.get("data"), context)

    elif event.get(
        "StackId"
    ) is not None and "arn:aws:cloudformation" in event.get("StackId"):
        cfn_handler(event, context)

    else:
        raise TypeError("The event is from unknown source type")
