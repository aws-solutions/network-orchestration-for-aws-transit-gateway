# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Init module, setting up loggers"""

import logging

logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("urllib").setLevel(logging.CRITICAL)
