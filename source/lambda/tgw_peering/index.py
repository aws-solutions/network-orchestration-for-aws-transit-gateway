# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Transit Gateway peering lambda"""

import logging
import asyncio
from os import environ
from tgw_peering.lib.utils import setup_logger
from tgw_peering.lib.tgw_peering_helper import (
    validate_tag,
    tag_event_router,
)

setup_logger(environ.get("LOG_LEVEL"))
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
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
        return

    try:
        asyncio.run(async_handler(event))
    except Exception as err:
        logger.error(str(err))


async def async_handler(event):
    """asynchronous lambda handler

    Args:
        event (dict): lambda triggering event
    """
    await tag_event_router(
        event["detail"]["tags"][environ.get("TGW_PEERING_TAG")]
    )
