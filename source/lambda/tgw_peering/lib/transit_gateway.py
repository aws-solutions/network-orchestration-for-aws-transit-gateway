# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from os import environ

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError, WaiterError, ParamValidationError
from botocore.waiter import WaiterModel
from botocore.waiter import create_waiter_with_client

from tgw_peering.lib.utils import TGWPeer, AttachmentState, boto3_config


class TGWPeering:

    def __init__(self):
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.ec2_client = boto3.client("ec2", config=boto3_config)

    def get_tgw_peers(
        self,
        tgw_id: str,
        states: list[AttachmentState],
    ) -> list[TGWPeer]:
        """Describe the tgw peering attachments for the tagged tgw id

        Args:
            tgw_id (str): tgw id of the tagged transit gateway

        Returns:
            list[TGWPeer]: list of transit gateway peers

        Raises:
            ClientError
        """
        log_message = {
            "METHOD": "describe_tgw_peering_attachments",
            "MESSAGE": f"getting tgw peering attachment list for {tgw_id} in states {states}",
        }
        self.logger.debug(str(log_message))
        try:
            tgw_peering_attachment_list: list[TGWPeer] = []

            paginator = self.ec2_client.get_paginator(
                "describe_transit_gateway_peering_attachments"
            )
            page_iterator = paginator.paginate(
                Filters=[
                    {"Name": "state", "Values": [s.value for s in states]},
                    {
                        "Name": "transit-gateway-id",
                        "Values": [tgw_id],
                    },
                    {
                        "Name": "tag:SolutionId",
                        "Values": [environ.get("SOLUTION_ID")],
                    },
                ],
            )
            for page in page_iterator:
                for attachment in page.get("TransitGatewayPeeringAttachments"):
                    tgw_peering_attachment_list.append(
                        TGWPeer(
                            transit_gateway=attachment["AccepterTgwInfo"][
                                "TransitGatewayId"
                            ],
                            aws_region=attachment["AccepterTgwInfo"]["Region"],
                            attachment_id=attachment[
                                "TransitGatewayAttachmentId"
                            ],
                        )
                    )
            return tgw_peering_attachment_list
        except ClientError as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            return []

    def create_tgw_peering_attachment(
        self,
        tgw_id: str,
        peer: TGWPeer,
        peer_account_id=None,
    ) -> dict:
        """Create tgw peering attachment

        Args:
            tgw_id (str):  tgw id of the local region
            peer_tgw_id (str): ID of the peer tgw with which to create the peering attachment
            peer_account_id (str): ID of the AWS account that owns the peer tgw
            peer_region (str): region where the peer tgw is located

        Returns:
            dict: details for the tgw peering attachment

        Raises:
            ClientError
        """
        log_message = {
            "METHOD": "create_tgw_peering_attachments",
            "MESSAGE": f"creating attachment for {tgw_id} with peer {peer.transit_gateway}",
        }
        self.logger.debug(str(log_message))
        if not peer_account_id:
            peer_account_id = environ.get("AWS_ACCOUNT")
        try:
            response = (
                self.ec2_client.create_transit_gateway_peering_attachment(
                    TransitGatewayId=tgw_id,
                    PeerTransitGatewayId=peer.transit_gateway,
                    PeerAccountId=peer_account_id,
                    PeerRegion=peer.aws_region,
                    TagSpecifications=[
                        {
                            "ResourceType": "transit-gateway-attachment",
                            "Tags": [
                                {
                                    "Key": "SolutionId",
                                    "Value": environ.get("SOLUTION_ID"),
                                },
                            ],
                        }
                    ],
                )
            )
            return response.get("TransitGatewayPeeringAttachment")
        except (ParamValidationError, ClientError) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    def delete_tgw_peering_attachment(self, peer: TGWPeer) -> None:
        """Delete tgw peering attachment

        Args:
            tgw_attach_id (str): tgw peering attachment to delete

        Raise:
            KeyError
            ClientError
        """
        log_message = {
            "METHOD": "delete_transit_gateway_peering_attachment",
            "MESSAGE": f"deleting tgw peering attachment {peer.attachment_id}",
        }
        self.logger.debug(str(log_message))
        try:
            self.ec2_client.delete_transit_gateway_peering_attachment(
                TransitGatewayAttachmentId=peer.attachment_id
            )
        except (KeyError, ClientError) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    async def accept_tgw_peering_attachment(self, peer: TGWPeer) -> None:
        """Accepts a transit gateway peering attachment request

        Args:
            tgw_attach_id (str): ID of the tgw attachment

        Raise:
            WaiterError, ClientError
        """

        log_message = {
            "METHOD": "accept_transit_gateway_peering_attachment",
            "MESSAGE": f"accepting tgw peering attachment for {peer}",
        }
        self.logger.debug(str(log_message))
        try:
            self.tgw_attachment_waiter(
                desired_state=AttachmentState.PENDING_ACCEPTANCE,
                attachment_id=peer.attachment_id,
            )  # waiter for the attachment to be in PENDING_ACCEPTANCE state
            _ec2_client = boto3.client(
                "ec2", region_name=peer.aws_region, config=boto3_config
            )
            _ec2_client.accept_transit_gateway_peering_attachment(
                TransitGatewayAttachmentId=peer.attachment_id
            )
        except (WaiterError, ClientError) as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    def tgw_attachment_waiter(
        self, desired_state: AttachmentState, attachment_id: str
    ) -> None:
        """[summary]

        Args:
            desired_state (str): desired state of the tgw attachment
            attachment_id (str): attachment-id
        """
        delay = 10
        max_attempts = 15
        waiter_name = "TGWAttachmentInPendingAcceptance"
        waiter_config = {
            "version": 2,
            "waiters": {
                "TGWAttachmentInPendingAcceptance": {
                    "operation": "DescribeTransitGatewayPeeringAttachments",
                    "delay": delay,
                    "maxAttempts": max_attempts,
                    "acceptors": [
                        {
                            "matcher": "path",
                            "expected": desired_state.value,
                            "argument": "TransitGatewayPeeringAttachments[0].State",
                            "state": "success",
                        },
                        {
                            "matcher": "path",
                            "expected": AttachmentState.FAILED.value,
                            "argument": "TransitGatewayPeeringAttachments[0].State",
                            "state": "failure",
                        },
                    ],
                }
            },
        }

        waiter_model = WaiterModel(waiter_config)
        custom_waiter = create_waiter_with_client(
            waiter_name, waiter_model, self.ec2_client
        )
        try:
            custom_waiter.wait(TransitGatewayAttachmentIds=[attachment_id])
        except WaiterError as err:
            self.logger.error(str(err))
            raise
