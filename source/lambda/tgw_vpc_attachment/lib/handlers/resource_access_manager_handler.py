# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import os
from os import environ

from aws_lambda_powertools import Logger

from tgw_vpc_attachment.lib.clients.ram import RAM
from tgw_vpc_attachment.lib.clients.sts import STS

EXECUTING = "Executing: "


class ResourceAccessManager:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.sts = STS()
        self.logger.info(event)

    """ This function accepts resource invitation in the spoke account. This is applicable
     to the scenario if the accounts are not in the AWS Organization."""

    def accept_resource_share_invitation(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            # check the invitation status if the accounts are not in AWS Organization
            arn = f"arn:{environ.get('PARTITION')}:organizations"
            if arn not in environ.get("FIRST_PRINCIPAL"):
                self._accept_pending()
            return self.event
        except Exception as e:
            self.logger.exception(str(e))
            raise

    def _accept_pending(self):
        self.ram = self._ram_client()
        invitation_list = self._get_resource_share_invitations()

        for invitation in invitation_list:
            sts = STS()
            if invitation.get("status") == "PENDING" and invitation.get("senderAccountId") == sts.get_account_id():
                self._accept(invitation)
            else:
                self._ignore(invitation)

    def _ram_client(self):
        account_id = self.event.get("account")
        credentials = self.sts.assume_transit_network_execution_role(account_id)
        region = self.event.get("region")
        return RAM(region, credentials=credentials)

    def _get_resource_share_invitations(self):
        arn = environ.get("RESOURCE_SHARE_ARN")
        invitation_list = self.ram.get_resource_share_invitations(arn)
        self.logger.debug("Get Resource Share Invitation Response")
        self.logger.debug(invitation_list)  # would always be single item in the response list
        return invitation_list

    def _accept(self, invitation):
        invitation_arn = invitation.get("resourceShareInvitationArn")
        response = self.ram.accept_resource_share_invitation(invitation_arn)
        self.logger.info(f"Printing {'Accept Resource Share Response'}")
        self.logger.info(response)
        resource_share_arn = invitation.get("resourceShareArn")
        self.event.update({"ResourceShareArnAccepted": resource_share_arn})

    def _ignore(self, invitation):
        self.logger.info("PENDING resource share not found in the spoke account.")
        self.event.update({"ResourceShareArnAccepted": invitation.get("None")})
