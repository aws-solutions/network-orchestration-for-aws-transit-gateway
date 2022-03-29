# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Organizations module"""

import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
from state_machine.lib.sts import STS
from state_machine.lib.boto3_config import boto3_config


class Organizations:
    """Class to handle Organizations methods"""

    def __init__(self):
        """Initialize the Organizations object's attributes"""
        self.logger = logging.getLogger(__name__)
        self.log_message = {}

        credentials = None
        org_role_arn = os.environ.get("ORGANIZATION_ACCOUNT_ROLE_ARN", "")

        if org_role_arn != "":
            sts = STS()
            credentials = sts.assume_role(org_role_arn, "stno-get-org-details")

        if credentials is not None:
            self.org_client = boto3.client(
                "organizations",
                config=boto3_config,
                aws_access_key_id=credentials.get("AccessKeyId"),
                aws_secret_access_key=credentials.get("SecretAccessKey"),
                aws_session_token=credentials.get("SessionToken"),
            )
        else:
            self.org_client = boto3.client("organizations", config=boto3_config)

    def get_account_name(self, account_id):
        """Retrieves AWS Organizations-related information about the specified account

        Args:
            account_id (string): The AWS account id that you want information about

        Returns:
            string: account name
        """
        self.log_message = {
            "METHOD": "get_account_name",
            "MESSAGE": f"getting account name for: XXXXXXXX{account_id[-4:]}",
        }
        self.logger.debug(json.dumps(self.log_message, indent=4))
        try:
            response = self.org_client.describe_account(AccountId=account_id)
            account_name = response.get("Account").get("Name")
            return account_name
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.warning(json.dumps(self.log_message, indent=4))
            return None

    def get_ou_name(self, ou_id):
        """Retrieves information about an organizational unit (OU)

        Args:
            ou_id (string): The unique id (ID) of the OU that you want details about

        Returns:
            string: OU name
        """
        self.log_message = {
            "METHOD": "get_ou_name",
            "MESSAGE": f"getting OU name for: {ou_id[-4:]}",
        }
        self.logger.debug(json.dumps(self.log_message, indent=4))
        try:
            response = self.org_client.describe_organizational_unit(
                OrganizationalUnitId=ou_id
            )
            ou_name = response.get("OrganizationalUnit").get("Name")
            return ou_name
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.warning(json.dumps(self.log_message, indent=4))
            return None

    def get_ou_path(self, account_id):
        """Retrieves Organization path for the given account

        Args:
            account_id (string): The AWS account id that you want information about

        Returns:
            string: OU path for the account
        """
        self.log_message = {
            "METHOD": "get_ou_path",
            "MESSAGE": f"getting OU path for: XXXXXXXX{account_id[-4:]}",
        }
        self.logger.debug(json.dumps(self.log_message, indent=4))
        current_id = account_id
        ou_path = []
        try:
            response = self.org_client.list_parents(ChildId=current_id)
            self.logger.debug(f"response is {response}")
            while response["Parents"][0]["Type"] != "Root":
                parent_id = response["Parents"][0]["Id"]
                self.logger.debug(f"parent id is : {parent_id}")
                ou_name = self.get_ou_name(parent_id)
                if not ou_name:
                    break
                ou_path.append(ou_name)
                current_id = parent_id
                response = self.org_client.list_parents(ChildId=current_id)
            ou_path.append("Root")
            ou_path.reverse()
            ou_path_string = "/".join(ou_path) + "/"
            self.logger.debug(
                f"get_ou_path({account_id}) returning: {ou_path_string}"
            )
            self.logger.debug(f"Returning ou path as {ou_path_string}")
            return ou_path_string
        except Exception as e:
            self.log_message["EXCEPTION"] = str(e)
            self.logger.warning(json.dumps(self.log_message, indent=4))
            return None
