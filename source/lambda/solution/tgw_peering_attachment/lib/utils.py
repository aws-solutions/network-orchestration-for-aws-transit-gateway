# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

import os
from dataclasses import dataclass
from enum import Enum
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


boto3_config = Config(
    retries={"max_attempts": 5, "mode": "standard"},
    user_agent_extra=os.environ.get("USER_AGENT_STRING", None),
)
