#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Setting up pytest fixtures for metrics collector tests"""

import os
import pytest

# Set USER_AGENT_STRING at module level before any imports
os.environ['USER_AGENT_STRING'] = 'AwsSolution/SO0058/v1.0.0'


@pytest.fixture(scope="module", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["SOLUTION_ID"] = "SO0058"
    os.environ["TGW_ID"] = "tgw-0123456789abcdef0"
    os.environ["AWS_ACCOUNT_ID"] = "123456789012"
    os.environ["STACK_ID"] = "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/12345678-1234-1234-1234-123456789012"
    os.environ["SOLUTION_UUID"] = "12345678-1234-1234-1234-123456789012"
    os.environ["SOLUTION_VERSION"] = "v1.0.0"
    os.environ["METRICS_FLAG"] = "Yes"
    os.environ["LOG_LEVEL"] = "INFO"
