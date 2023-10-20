# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Transit Gateway test module"""

import asyncio
from os import environ
import pytest
from botocore.stub import Stubber
from botocore.exceptions import ClientError, WaiterError
from moto import mock_ec2
from tgw_peering_attachment.lib.transit_gateway import TGWPeering
from tgw_peering_attachment.lib.utils import TGWPeer, AttachmentState


# pylint:disable=no-self-use
# using classes for unit-test grouping and running tests with class node-ids
@pytest.mark.TDD
@mock_ec2
class TestGetPeers:
    """TDD test class for TGW describe peering attachment methods"""

    def test__success(self):
        """success"""
        tgw = TGWPeering()

        # mock setup
        sample_tgw1 = tgw.ec2_client.create_transit_gateway()
        peers = tgw.get_tgw_peers(
            tgw_id=sample_tgw1["TransitGateway"]["TransitGatewayId"],
            states=[AttachmentState.AVAILABLE],
        )
        assert len(peers) == 0
        # clean-up
        tgw.ec2_client.delete_transit_gateway(
            TransitGatewayId=sample_tgw1["TransitGateway"]["TransitGatewayId"]
        )

    def test__fail__client_error(self):
        """fail with client error"""
        tgw = TGWPeering()
        stubber = Stubber(tgw.ec2_client)
        stubber.add_client_error(
            "describe_transit_gateway_peering_attachments",
            service_error_code="InternalException",
            service_message="this is test error",
        )
        stubber.activate()
        peers = tgw.get_tgw_peers(
            tgw_id="",
            states=[AttachmentState.AVAILABLE],
        )
        assert len(peers) == 0
        stubber.deactivate()


@pytest.mark.BDD
@mock_ec2
class TestCreatePeeringAttachment:
    """BDD test class for TGW create peering attachment methods"""

    owner = "123456789012"

    def test__success(self):
        """success"""
        tgw = TGWPeering()

        # mock setup
        sample_tgw1 = tgw.ec2_client.create_transit_gateway()
        sample_tgw2 = tgw.ec2_client.create_transit_gateway()
        sample_peer = TGWPeer(
            transit_gateway=sample_tgw2["TransitGateway"]["TransitGatewayId"],
            aws_region=environ.get("AWS_DEFAULT_REGION"),
        )
        attachment = tgw.create_tgw_peering_attachment(
            tgw_id=sample_tgw1["TransitGateway"]["TransitGatewayId"],
            peer=sample_peer,
            peer_account_id=self.owner,
        )

        sample_peer.attachment_id = attachment["TransitGatewayAttachmentId"]

        # test attachment is tagged with solution identifier
        assert attachment["Tags"][0]["Key"] == "SolutionId"
        assert attachment["Tags"][0]["Value"] == environ.get("SOLUTION_ID")

        peers = tgw.get_tgw_peers(
            tgw_id=sample_tgw1["TransitGateway"]["TransitGatewayId"],
            states=[AttachmentState.AVAILABLE, AttachmentState.PENDING_ACCEPTANCE],
        )

        assert isinstance(peers[0], TGWPeer)
        assert peers[0] == sample_peer

        # clean-up
        tgw.ec2_client.delete_transit_gateway_peering_attachment(
            TransitGatewayAttachmentId=attachment["TransitGatewayAttachmentId"]
        )
        tgw.ec2_client.delete_transit_gateway(
            TransitGatewayId=sample_tgw1["TransitGateway"]["TransitGatewayId"]
        )
        tgw.ec2_client.delete_transit_gateway(
            TransitGatewayId=sample_tgw2["TransitGateway"]["TransitGatewayId"]
        )

    def test__fail__client_error(self):
        """fail with client error"""

        tgw = TGWPeering()
        stubber = Stubber(tgw.ec2_client)
        _err_code = "InternalException"
        _message = "test error"
        stubber.add_client_error(
            "create_transit_gateway_peering_attachment",
            service_error_code=_err_code,
            service_message=_message,
        )
        stubber.activate()
        peer = TGWPeer(transit_gateway="", aws_region="")
        with pytest.raises(ClientError) as err:
            tgw.create_tgw_peering_attachment(
                tgw_id="", peer=peer, peer_account_id=""
            )
        assert err.value.response["Error"]["Code"] == _err_code
        assert err.value.response["Error"]["Message"] == _message
        stubber.deactivate()


@pytest.mark.TDD
@mock_ec2
class TestDeletePeeringAttachment:
    """TDD test class for TGW create peering attachment methods"""

    def test__success(self):
        """success"""
        tgw = TGWPeering()

        # mock setup
        attachment = tgw.ec2_client.create_transit_gateway_peering_attachment(
            TransitGatewayId="",
            PeerTransitGatewayId="",
            PeerAccountId="",
            PeerRegion="",
        )["TransitGatewayPeeringAttachment"]
        peer = TGWPeer(
            aws_region="",
            transit_gateway="",
            attachment_id=attachment["TransitGatewayAttachmentId"],
        )
        tgw.delete_tgw_peering_attachment(peer)

    def test__fail__key_error(self):
        """fail with key error"""
        tgw = TGWPeering()
        peer = TGWPeer(
            aws_region="",
            transit_gateway="",
            attachment_id="",
        )
        with pytest.raises(KeyError):
            tgw.delete_tgw_peering_attachment(peer)

    def test__fail__client_error(self):
        """fail with client error"""

        tgw = TGWPeering()
        peer = TGWPeer(
            aws_region="",
            transit_gateway="",
            attachment_id="",
        )
        stubber = Stubber(tgw.ec2_client)
        _err_code = "InternalException"
        _message = "test error"
        stubber.add_client_error(
            "delete_transit_gateway_peering_attachment",
            service_error_code=_err_code,
            service_message=_message,
        )
        stubber.activate()
        with pytest.raises(ClientError) as err:
            tgw.delete_tgw_peering_attachment(peer)
        assert err.value.response["Error"]["Code"] == _err_code
        assert err.value.response["Error"]["Message"] == _message
        stubber.deactivate()


@pytest.mark.BDD
@mock_ec2
class TestAcceptPeeringAttachment:
    """TDD test class for TGW accept_peering_attachment methods"""

    def test__success(self, mocker):
        """success"""
        tgw = TGWPeering()
        peer = TGWPeer(
            aws_region="",
            transit_gateway="",
            attachment_id="",
        )
        mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.tgw_attachment_waiter",
            side_effect=WaiterError(
                name="TestWaiter",
                reason="error message",
                last_response="waiter_failed",
            ),
        )
        with pytest.raises(WaiterError) as err:
            asyncio.run(tgw.accept_tgw_peering_attachment(peer))
        assert str(err.value.last_response) == "waiter_failed"
