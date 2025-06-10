# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
from os import environ

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from solution.tgw_peering_attachment.lib.tgw_peering_helper import (
    validate_tag,
    tag_event_router,
)

logger = Logger(level=os.getenv('LOG_LEVEL'), service="TGW_PEERING_ATTACHMENT")


def lambda_handler(event, context: LambdaContext):
    """handler for tgw peering microservice

    Args:
        event (dict): lambda triggering event
        context (object): lambda context object to the handler

    Note: lambda does not support async handlers for python runtimes
    """
    logger.info("Entering tgw-peering lambda_handler")
    logger.debug(event)
    try:
        validate_tag(event)
        environ["AWS_ACCOUNT"] = context.invoked_function_arn.split(":")[4]
    except KeyError:
        logger.warning("%s key deleted", environ.get("TGW_PEERING_TAG"))
        return
    except ValueError as err:
        logger.warning("%s - %s", environ.get("TGW_PEERING_TAG"), str(err))
        if str(err) != "DELETE_TAG":
            return
    except Exception as err:
        logger.error("%s - %s", environ.get("TGW_PEERING_TAG"), str(err))
        raise

    try:
        asyncio.run(async_handler(event))
    except Exception as err:
        logger.error(str(err))
        raise


async def async_handler(event):
    """asynchronous lambda handler

    Args:
        event (dict): lambda triggering event
    """
    await tag_event_router(
        event["detail"]["tags"][environ.get("TGW_PEERING_TAG")]
    )
