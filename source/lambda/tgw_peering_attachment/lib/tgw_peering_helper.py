# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import re
from os import environ

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from tgw_peering_attachment.lib.transit_gateway import TGWPeering
from tgw_peering_attachment.lib.utils import TGWPeer, AttachmentState

logger = Logger(os.getenv('LOG_LEVEL'))


def validate_tag(event: dict):
    """Validates if the transit gateway tag is consistent with the format

    Args:
        event (dict): lambda triggering event

    Raises:
        ValueError: for empty and invalid tag value
        Exception: general exception for all other errors
    """
    logger.debug("validating tgw tag value")
    # pylint:disable=line-too-long
    tgw_peer_regex = r"^tgw-[0-9a-z]{17}_(us(-gov)?|ap|ca|cn|eu|sa)-(central|north|(north(?:east|west))|south|south(?:east|west)|east|west)-\d+$"
    peers = event["detail"]["tags"][environ.get("TGW_PEERING_TAG")]
    if peers == "":
        raise ValueError("EMPTY_TAG")
    if peers.upper() == "DELETE":
        raise ValueError("DELETE_TAG")
    peers_list = peers.split("/")
    for peer in peers_list:
        if re.match(tgw_peer_regex, peer) is None:
            raise ValueError("INVALID_TAG")


async def tag_event_router(tag_value: str) -> None:
    """Handles tag events for transit gateway

    The tag_value string is composed of multiple elements seperated by the slash character '/'.
    Each element consists of a tgw id and an aws region seperated by underscore '_' character.
    Example: tgw-010101010abababab_us-east-1/tgw-010101011abababab_us-east-2
    """
    logger.debug("handling tgw tag event")
    hub_tgw_id = environ.get("TGW_ID")
    tgw = TGWPeering()
    current_peers: list[TGWPeer] = tgw.get_tgw_peers(
        tgw_id=hub_tgw_id,
        states=[
            AttachmentState.AVAILABLE,
            AttachmentState.INITIATING,
            AttachmentState.INITIATING_REQUEST,
            AttachmentState.PENDING,
            AttachmentState.PENDING_ACCEPTANCE,
            AttachmentState.MODIFYING,
        ],
    )

    logger.debug("current tgw peers %s", current_peers)
    current_peer_tgw_ids: list[str] = [i.transit_gateway for i in current_peers]

    if tag_value.upper() == "DELETE":
        await delete_all_peering_attachments(current_peers, tgw)
    else:
        await create_new_peering_attachments(current_peer_tgw_ids, hub_tgw_id, tag_value, tgw)

        await delete_undesired_peering_attachments(current_peers, tag_value, tgw)

        await accept_all_peering_requests(hub_tgw_id, tgw)


async def delete_all_peering_attachments(current_peers, tgw):
    for peer in current_peers:
        try:
            tgw.delete_tgw_peering_attachment(peer)
        except ClientError as err:
            logger.warning(str(err))


async def create_new_peering_attachments(current_peer_tgw_ids, hub_tgw_id, tag_value, tgw):
    for peer_string in tag_value.split("/"):
        split = peer_string.split("_")
        transit_gateway_id = split[0]
        region = split[1]

        if transit_gateway_id not in current_peer_tgw_ids:
            try:
                tgw.create_tgw_peering_attachment(
                    tgw_id=hub_tgw_id,
                    peer=TGWPeer(transit_gateway=transit_gateway_id, aws_region=region)
                )
            except ClientError as err:
                logger.warning(str(err))


async def delete_undesired_peering_attachments(current_peers, tag_value, tgw):
    # determine desired peers according to the new tag value
    desired_peer_tgw_ids: list[str] = [peer_string.split("_")[0] for peer_string in tag_value.split("/")]

    # determine which peers from the current state are no longer desired
    peers_to_delete = [peer for peer in current_peers if peer.transit_gateway not in desired_peer_tgw_ids]
    for peer in peers_to_delete:
        try:
            tgw.delete_tgw_peering_attachment(peer)
        except (KeyError, ClientError) as err:
            logger.warning(str(err))


async def accept_all_peering_requests(hub_tgw_id, tgw):
    # accept all peering requests
    peering_requests: list[TGWPeer] = tgw.get_tgw_peers(
        tgw_id=hub_tgw_id,
        states=[
            AttachmentState.INITIATING,
            AttachmentState.INITIATING_REQUEST,
        ],
    )
    coros = [
        tgw.accept_tgw_peering_attachment(peer) for peer in peering_requests
    ]
    await asyncio.gather(*coros, return_exceptions=True)  # fail silently
    logger.info(
        "peering requests accepted, for failed requests turn debug mode and check logs"
    )
