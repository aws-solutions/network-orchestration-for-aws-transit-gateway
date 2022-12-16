# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Security Token Service module"""

import json
import os
from os import environ

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from mypy_boto3_sts import STSClient
from mypy_boto3_sts.type_defs import CredentialsTypeDef, GetCallerIdentityResponseTypeDef

from state_machine.lib.clients.boto3_config import boto3_config


class STS:
    def __init__(self):
        """Initialize the STS object's attributes"""
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.log_message = {}
        self.sts_client: STSClient = boto3.client("sts", config=boto3_config)

    def assume_transit_network_execution_role(
            self,
            account_id: str
    ) -> CredentialsTypeDef:
        try:
            role_name = "TransitNetworkExecutionRole"
            role_arn = (
                    "arn:aws:iam::"
                    + str(account_id)
                    + ":role/"
                    + role_name
                    + "-"
                    + environ.get("AWS_REGION")
            )
            session_name = "transit-network-role"
            credentials = self.assume_role(role_arn, session_name)
            return credentials
        except Exception as error:
            self.logger.exception(
                f"Error while assuming role TransitNetworkExecutionRole: {error}"
            )
            raise

    def assume_role(
            self,
            role_arn: str,
            session_name: str,
            duration_in_seconds=900
    ) -> CredentialsTypeDef:
        """Returns a set of temporary security credentials that you can use to access AWS resources

        Args:
            role_arn (string): The Amazon Resource Name (ARN) of the role to assume
            session_name (string): An identifier for the assumed role session
            duration_in_seconds (int, optional):  duration, in seconds, of the role session. Defaults to 900.
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
                DurationSeconds=duration_in_seconds,
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
            caller_identity: GetCallerIdentityResponseTypeDef = self.sts_client.get_caller_identity()
            return caller_identity.get("Account")
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.error(json.dumps(self.log_message, indent=4))
            raise
