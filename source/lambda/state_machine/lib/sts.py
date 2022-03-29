# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""STS module"""

import json
import logging
import boto3
from botocore.exceptions import ClientError
from state_machine.lib.boto3_config import boto3_config


class STS:
    """Class to handle STS methods"""

    def __init__(self):
        """Initialize the STS object's attributes"""
        self.logger = logging.getLogger(__name__)
        self.log_message = {}
        self.sts_client = boto3.client("sts", config=boto3_config)

    def assume_role(self, role_arn, session_name, duration=900):
        """Returns a set of temporary security credentials that you can use to access AWS resources

        Args:
            role_arn (string): The Amazon Resource Name (ARN) of the role to assume
            session_name (string): An identifier for the assumed role session
            duration (int, optional):  duration, in seconds, of the role session. Defaults to 900.

        Returns:
            dict: temporary security credentials

            {
                'AccessKeyId': 'string',
                'SecretAccessKey': 'string',
                'SessionToken': 'string',
                'Expiration': datetime(2015, 1, 1)
            }
        """
        self.log_message = {
            "METHOD": "assume_role",
            "MESSAGE": f"assuming role: {role_arn}",
        }
        self.logger.debug(self.log_message)
        try:
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                DurationSeconds=duration,
            )
            return response["Credentials"]
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.error(json.dumps(self.log_message, indent=4))
            raise

    def get_account_id(self):
        """Get account id for the caller

        Returns:
            string: 12 digit AWS account id
        """
        self.log_message = {
            "METHOD": "get_account_id",
            "MESSAGE": "getting account id",
        }
        self.logger.debug(self.log_message)
        try:
            return self.sts_client.get_caller_identity().get("Account")
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.error(json.dumps(self.log_message, indent=4))
            raise
