# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

from dataclasses import dataclass
from enum import Enum
import json
import logging
import os
from typing import Optional
from botocore.config import Config


@dataclass
class TGWPeer:
    """Transit Gateway peer data type

    Attributes:
        transit_gateway: peer transit gateway id
        aws_region: region where tgw exists
        attachment_id: tgw attachment id for the peering tgw
    """

    transit_gateway: str
    aws_region: str
    attachment_id: Optional[str] = None


class AttachmentState(Enum):
    """Class derived from enum class

    Args:
        Enum (class): Base class for creating enumerated constants
    """

    PENDING_ACCEPTANCE = "pendingAcceptance"
    INITIATING_REQUEST = "initiatingRequest"
    INITIATING = "initiating"
    FAILED = "failed"
    MODIFYING = "modifying"
    PENDING = "pending"
    AVAILABLE = "available"


def setup_logger(log_level):
    """function to setup root logger

    Args:
        log_level (string): log level info, debug, warn, error etc.
    """
    loglevel = logging.getLevelName(log_level.upper())
    root_logger = logging.getLogger()
    root_logger.setLevel(loglevel)

    # pylint: disable=line-too-long
    logformat = json.dumps(
        {
            "timestamp": "%(asctime)s",
            "module": "%(name)s",
            "log_level": "%(levelname)s",
            "log_message": "%(message)s",
        }
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(logformat))

    if len(root_logger.handlers) == 0:
        root_logger.addHandler(stream_handler)
    else:
        root_logger.handlers[0] = stream_handler


boto3_config = Config(
    retries={"max_attempts": 5, "mode": "standard"},
    user_agent_extra=os.environ.get("USER_AGENT_STRING", None),
)
