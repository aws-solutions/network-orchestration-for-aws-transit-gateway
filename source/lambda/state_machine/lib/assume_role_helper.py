# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Assume role helper module"""

from os import environ
import logging
from state_machine.lib.sts import STS


class AssumeRole:
    """Class to handle methods for assuming role and using credentials"""

    def __init__(self):
        """Initialize the AssumeRole object's attributes"""
        self.logger = logging.getLogger(__name__)

    def __call__(self, account):
        try:
            sts = STS()
            role_name = "TransitNetworkExecutionRole"
            role_arn = (
                "arn:aws:iam::"
                + str(account)
                + ":role/"
                + role_name
                + "-"
                + environ.get("AWS_REGION")
            )
            session_name = "transit-network-role"
            # assume role
            credentials = sts.assume_role(role_arn, session_name)
            return credentials
        except Exception as error:
            self.logger.exception(
                f"Error while assuming role TransitNetworkExecutionRole: {error}"
            )
            raise
