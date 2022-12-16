# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import List

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_ram.type_defs import GetResourceShareInvitationsResponseTypeDef, ResourceShareInvitationTypeDef

from state_machine.lib.clients.boto3_config import boto3_config


class RAM:

    def __init__(self, region, **kwargs):
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.logger.debug(
            "Setting up RAM BOTO3 Client with ASSUMED ROLE credentials"
        )
        cred = kwargs.get("credentials")
        self.ram_client = boto3.client(
            "ram",
            region_name=region,
            config=boto3_config,
            aws_access_key_id=cred.get("AccessKeyId"),
            aws_secret_access_key=cred.get("SecretAccessKey"),
            aws_session_token=cred.get("SessionToken"),
        )

    def get_resource_share_invitations(self, resource_share_arn) -> List[ResourceShareInvitationTypeDef]:
        """
        This method gets resource share invitations for given resource share arn
        :param resource_share_arn: ARN for the resource
        :return: list of invitations:
        """
        try:
            response: GetResourceShareInvitationsResponseTypeDef = self.ram_client.get_resource_share_invitations(
                resourceShareArns=[resource_share_arn]
            )
            invitation_list = response.get("resourceShareInvitations", [])
            return invitation_list
        except Exception as error:
            self.logger.exception(
                f"Error while getting resource share invitations for arn {resource_share_arn}"
            )
            self.logger.exception(error)
            raise

    def accept_resource_share_invitation(self, resource_share_invitation_arn):
        """
        This method accepts resource share invitations for given resource share arn
        :param resource_share_invitation_arn: ARN for resource share invitation
        """
        try:
            response = self.ram_client.accept_resource_share_invitation(
                resourceShareInvitationArn=resource_share_invitation_arn
            )
            return response.get("resourceShareInvitation")
        except Exception as error:
            self.logger.exception(
                f"Error while accepting resource share invitations for arn {resource_share_invitation_arn}"
            )
            self.logger.exception(error)
            raise
