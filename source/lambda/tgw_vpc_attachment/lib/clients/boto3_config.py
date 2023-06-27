# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""boto3 config module"""
import os

import botocore

boto3_config = botocore.config.Config(
  retries={
      'max_attempts': 5,
      'mode': 'standard'
  },
  user_agent_extra=os.environ['USER_AGENT_STRING']
)
