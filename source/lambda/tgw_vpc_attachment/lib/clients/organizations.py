# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from mypy_boto3_organizations import OrganizationsClient
from mypy_boto3_organizations.type_defs import DescribeAccountResponseTypeDef, DescribeOrganizationalUnitResponseTypeDef
from typing import Union

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from tgw_vpc_attachment.lib.clients.boto3_config import boto3_config
from tgw_vpc_attachment.lib.clients.sts import STS


class Organizations:

    def __init__(self):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.log_message = {}

        credentials = None
        org_role_arn = os.environ.get("ORGANIZATION_ACCOUNT_ROLE_ARN", "")

        if org_role_arn != "":
            sts = STS()
            credentials = sts.assume_role(org_role_arn, "stno-get-org-details")

        if credentials is not None:
            self.org_client: OrganizationsClient = boto3.client(
                "organizations",
                config=boto3_config,
                aws_access_key_id=credentials.get("AccessKeyId"),
                aws_secret_access_key=credentials.get("SecretAccessKey"),
                aws_session_token=credentials.get("SessionToken"),
            )
        else:
            self.org_client: OrganizationsClient = boto3.client("organizations", config=boto3_config)

    def get_account_name(self, account_id: str) -> Union[str, None]:
        self.log_message = {
            "METHOD": "get_account_name",
            "MESSAGE": f"getting account name for: XXXXXXXX{account_id[-4:]}",
        }
        self.logger.debug(json.dumps(self.log_message, indent=4))
        try:
            response: DescribeAccountResponseTypeDef = self.org_client.describe_account(AccountId=account_id)
            account_name = response.get("Account").get("Name")
            return account_name
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.warning(json.dumps(self.log_message, indent=4))
            return None

    def get_ou_name(self, ou_id: str) -> Union[str, None]:
        self.log_message = {
            "METHOD": "get_ou_name",
            "MESSAGE": f"getting OU name for: {ou_id[-4:]}",
        }
        self.logger.debug(json.dumps(self.log_message, indent=4))
        try:
            response: DescribeOrganizationalUnitResponseTypeDef = self.org_client.describe_organizational_unit(
                OrganizationalUnitId=ou_id
            )
            return response.get("OrganizationalUnit").get("Name")
        except ClientError as err:
            self.log_message["EXCEPTION"] = str(err)
            self.logger.warning(json.dumps(self.log_message, indent=4))
            return None

    def get_ou_path(self, account_id: str):
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
