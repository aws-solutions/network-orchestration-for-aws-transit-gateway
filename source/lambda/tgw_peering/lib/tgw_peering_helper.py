# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import re
from os import environ

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from tgw_peering.lib.transit_gateway import TGWPeering
from tgw_peering.lib.utils import TGWPeer, AttachmentState

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
    tgw_peer_regex = r"^tgw-[0-9a-z]{17}_(us(-gov)?|ap|ca|cn|eu|sa)-(central|[(north|south)?(east|west)?]+)-\d$"
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

    Args:
        tag_value (str): tag value for the tgw tag-change event
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
    current_peer_tgw: list[str] = [i.transit_gateway for i in current_peers]

    # case of empty tag, delete all peering attachments
    if tag_value.upper() == "DELETE":
        for peer in current_peers:
            try:
                tgw.delete_tgw_peering_attachment(peer)
            except ClientError as err:
                logger.warning(str(err))
        return

    await create_new_and_delete_old_peering_attachments(current_peer_tgw, hub_tgw_id, tag_value, tgw)

    await delete_old_peering_attachments(current_peer_tgw, current_peers, tgw)

    await accept_all_peering_requests(hub_tgw_id, tgw)


async def create_new_and_delete_old_peering_attachments(current_peer_tgw, hub_tgw_id, tag_value, tgw):
    # for all other cases, create new and delete old peering attachments
    peer_list = tag_value.split("/")
    for peer in peer_list:
        peer = TGWPeer(
            transit_gateway=peer.split("_")[0], aws_region=peer.split("_")[1]
        )

        # creation of new peering attachments
        if peer.transit_gateway not in current_peer_tgw:
            try:
                tgw.create_tgw_peering_attachment(tgw_id=hub_tgw_id, peer=peer)
            except ClientError as err:
                logger.warning(str(err))
        else:
            current_peer_tgw.remove(peer.transit_gateway)


async def delete_old_peering_attachments(current_peer_tgw, current_peers, tgw):
    # deleting old peering attachments
    for peer in current_peers:
        if peer.transit_gateway in current_peer_tgw:
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
