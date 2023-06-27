# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import os
from os import environ

from aws_lambda_powertools import Logger

from tgw_vpc_attachment.lib.clients.ec2 import EC2
from tgw_vpc_attachment.lib.clients.sns import SNS
from tgw_vpc_attachment.lib.clients.sts import STS
from tgw_vpc_attachment.lib.handlers.dynamodb_handler import DynamoDb
from tgw_vpc_attachment.lib.utils.helper import timestamp_message

CLASS_EVENT = " Class Event"
EXECUTING = "Executing: "


class ApprovalNotification:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.spoke_account_id = self.event.get("account")
        self.spoke_region = environ.get("AWS_REGION")
        self.sts = STS()
        self.logger.debug(event)

    def _ec2_client(self, account_id):
        credentials = self.sts.assume_transit_network_execution_role(account_id)
        return EC2(credentials=credentials)

    def notify(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            approval_notifications = environ.get("APPROVAL_NOTIFICATION")
            if (
                    approval_notifications and approval_notifications.lower() == "yes"
                    and self.event.get("Status") == "requested"
            ):
                self._send_email()
                self.logger.info(
                    "Adding tag to VPC with the pending approval message"
                )
                if self.event.get("AssociationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCAssociation",
                        "Request to associate this VPC with requested TGW Routing Table is PENDING APPROVAL. "
                        "Contact your network admin for more information.",
                    )
                if self.event.get("PropagationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "Request to propagate this VPC to requested TGW Routing Table is PENDING APPROVAL. "
                        "Contact your network admin for more information.",
                    )
            elif (
                    self.event.get("Status") == "rejected"
                    or self.event.get("Status") == "auto-rejected"
            ):
                self.logger.info("Adding tag to VPC with the rejection message")
                if self.event.get("AssociationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCAssociation",
                        "Request to associate this VPC with requested TGW Routing Table has been REJECTED. "
                        "Contact your network admin for more information.",
                    )
                if self.event.get("PropagationNeedsApproval") == "yes":
                    self._create_tag(
                        self.event.get("VpcId"),
                        "VPCPropagation",
                        "Request to propagate this VPC to requested TGW Routing Table has been REJECTED. "
                        "Contact your network admin for more information. ",
                    )
            else:
                self.logger.info(
                    "Approval notifications are disabled. Please set CFN template variable "
                    "'ApprovalNotification' to 'Yes' if you wish to receive notifications."
                )
            return self.event
        except Exception as e:
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": inspect.stack()[0][3],
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _send_email(self):
        notify = SNS()
        topic_arn = environ.get("APPROVAL_NOTIFICATION_ARN")
        subject = "STNO: Transit Network Change Requested"
        message = (
            "A new request for VPC: '{}' to associate with TGW Route Table: '{}' and propagate to "
            "TGW Route Tables: '{}' is ready for review. Please use this link {} to login to the 'Transit Network "
            "Management Console' to approve or reject the request.".format(
                self.event.get("VpcId"),
                self.event.get("Associate-with").title(),
                ", ".join(self.event.get("Propagate-to")).title(),
                environ.get("STNO_CONSOLE_LINK"),
            )
        )
        self.logger.info("Message: {}".format(message))
        notify.publish(topic_arn, message, subject)
        self.logger.info("Notification sent to the network admin for approval.")

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ec2 = self._ec2_client(self.spoke_account_id)
            ec2.create_tags(
                resource, "STNOStatus-" + key, timestamp_message(message)
            )
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def _message(self, method, e):
        return {
            "FILE": __file__.split("/")[-1],
            "CLASS": self.__class__.__name__,
            "METHOD": method,
            "EXCEPTION": str(e),
        }

    def _update_ddb_failed(self, e):
        self.event.update({"Comment": str(e)})
        self.event.update({"Status": "failed"})
        ddb = DynamoDb(self.event)
        ddb.put_item()
