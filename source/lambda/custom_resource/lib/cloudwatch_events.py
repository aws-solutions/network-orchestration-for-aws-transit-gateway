# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""CloudWatch Events module"""

import logging
import re
import boto3
from botocore.exceptions import ClientError
from custom_resource.lib.utils import boto3_config


class CloudWatchEvents:
    """Class to handle CloudWatch Events methods"""

    def __init__(self):
        """Initialize the CloudWatchEvents object's attributes

        Args:
            None
        """
        self.logger = logging.getLogger(__name__)
        self.cwe_client = boto3.client("events", config=boto3_config)

    def put_permission(self, principal, event_bus_name):
        """Puts permission on CloudWatch event bus. Running it permits the specified\
            AWS account or AWS organization to put events to your account's default event bus

        Args:
            principal (string): 12-digit Amazon Web Services account ID or the Organization\
                 Arn that you are permitting to put events to specified event bus
            event_bus_name (string):  name of the event bus associated with the rule

        Returns:
            None: put_permission api response

        Raises:
            EventBridge.Client.exceptions.ResourceNotFoundException: \
                thrown when AWS resource not found
            ClientError: general exception provided by an AWS service to your Boto3 client's request
        """
        log_message = {
            "METHOD": "put_permission",
            "MESSAGE": f"putting permission on CloudWatch Event bus for principal:\
                 {principal}, event_bus_name: {event_bus_name}",
        }
        self.logger.debug(str(log_message))

        try:
            if re.match("(arn:aws:organizations:).*", principal):
                org_id = principal.split("/")[-1]
                condition = {
                    "Type": "StringEquals",
                    "Key": "aws:PrincipalOrgID",
                    "Value": org_id,
                }
                # Once we specify a condition with an AWS organization ID, the recommendation
                # is we use "*" as the value or Principal to grant permission to all the accounts
                #  in the named organization.
                self.cwe_client.put_permission(
                    Action="events:PutEvents",
                    Principal="*",
                    StatementId=org_id,
                    Condition=condition,
                    EventBusName=event_bus_name,
                )
            else:
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
        """Revokes the permission of another AWS account to be able to put events to\
             the specified event bus

        Args:
            principal (string): 12-digit Amazon Web Services account ID or the Organization\
                 Arn that you are permitting to put events to specified event bus
            event_bus_name (string): name of the event bus to revoke permissions for

        Returns:
            None: remove_permission api response

        Raises:
            ClientError: general exception provided by an AWS service to your Boto3 client's request
        """
        log_message = {
            "METHOD": "remove_permission",
            "MESSAGE": f"removing permission from CloudWatch Event bus principal:\
                 {principal}, event_bus_name: {event_bus_name}",
        }
        self.logger.debug(str(log_message))
        statement_id = (
            principal.split("/")[-1]
            if re.match("(arn:aws:organizations:).*", principal)
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
        """Displays details about the specified event bus in your account

        Args:
            event_bus_name (string): name of the event bus to describe

        Returns:
            dict: api response

            {
                'Name': 'string',
                'Arn': 'string',
                'Policy': 'string'
            }

        Raises:
            EventBridge.Client.exceptions.ResourceNotFoundException: \
                thrown when AWS resource not found
            ClientError: general exception provided by an AWS service to Boto3 client's request
        """
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
