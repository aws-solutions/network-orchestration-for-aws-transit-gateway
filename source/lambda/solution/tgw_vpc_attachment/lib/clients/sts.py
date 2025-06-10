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

from solution.tgw_vpc_attachment.lib.clients.boto3_config import boto3_config


class STS:
    def __init__(self):
        """Initialize the STS object's attributes"""
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.log_message = {}
        self.sts_client: STSClient = boto3.client("sts", config=boto3_config)

    def assume_transit_network_execution_role(
            self,
            account_id: str
    ) -> CredentialsTypeDef:
        try:
            role_name = "TransitNetworkExecutionRole"
            role_arn = (
                    "arn:"
                    + environ.get("PARTITION")
                    + ":iam::"
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
            raise error

    def assume_role(
            self,
            role_arn: str,
            session_name: str,
            duration_in_seconds=900
    ) -> CredentialsTypeDef:
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
