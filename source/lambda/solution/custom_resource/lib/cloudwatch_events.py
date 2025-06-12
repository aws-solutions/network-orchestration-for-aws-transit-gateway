# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from solution.custom_resource.lib.utils import boto3_config


class CloudWatchEvents:

    def __init__(self):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.cwe_client = boto3.client("events", config=boto3_config)
        self.partition = os.environ.get("PARTITION")

    def put_permission(self, principal, event_bus_name):
        log_message = {
            "METHOD": "put_permission",
            "MESSAGE": f"putting permission on CloudWatch Event bus for principal:\
                 {principal}, event_bus_name: {event_bus_name}",
        }
        self.logger.debug(str(log_message))

        try:
            if f"arn:{self.partition}:organizations" in principal:
                self.logger.info(f"Adding Organization ARN: {principal} in the policy condition")
                org_id = principal.split("/")[-1]
                condition = {
                    "Type": "StringEquals",
                    "Key": "aws:PrincipalOrgID",
                    "Value": org_id,
                }
                self.cwe_client.put_permission(
                    Action="events:PutEvents",
                    Principal="*",
                    StatementId=org_id,
                    Condition=condition,
                    EventBusName=event_bus_name,
                )
            else:
                self.logger.info(f"Adding Account ID: {principal} in the policy.")
                self.cwe_client.put_permission(
                    Action="events:PutEvents",
                    Principal=principal,
                    StatementId=principal,
                    EventBusName=event_bus_name,
                )
            return None  # the API response always returns None
        except (
            self.cwe_client.exceptions.ResourceNotFoundException,
            ClientError,
        ) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    def remove_permission(self, principal, event_bus_name):
        log_message = {
            "METHOD": "remove_permission",
            "MESSAGE": f"removing permission from CloudWatch Event bus principal:\
                 {principal}, event_bus_name: {event_bus_name}",
        }
        self.logger.debug(str(log_message))
        statement_id = (
            principal.split("/")[-1]
            if f"arn:{self.partition}:organizations" in principal
            else principal
        )
        try:
            self.cwe_client.remove_permission(
                StatementId=statement_id, EventBusName=event_bus_name
            )
            return None  # the API response if always return None
        except self.cwe_client.exceptions.ResourceNotFoundException as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.warning(str(log_message))
            return None
        except ClientError as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    def describe_event_bus(self, event_bus_name):
        log_message = {
            "METHOD": "describe_event_bus",
            "MESSAGE": f"describing CloudWatch Event bus event_bus_name: {event_bus_name}",
        }
        try:
            response = self.cwe_client.describe_event_bus(Name=event_bus_name)
            log_message["RESPONSE"] = response
            self.logger.debug(str(log_message))
            return response
        except (
            self.cwe_client.exceptions.ResourceNotFoundException,
            ClientError,
        ) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise
