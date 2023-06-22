# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Transit Gateway-helper test module"""

import asyncio
from copy import deepcopy
import os
import pytest
from tgw_peering_attachment.lib.tgw_peering_helper import validate_tag, tag_event_router
from tgw_peering_attachment.lib.utils import TGWPeer


# pylint:disable=no-self-use, invalid-name
# using classes for unit-test grouping and running tests with class node-ids
EC2_TAG_CHANGE_EVENT = {
    "state-machine": "arn:aws:states:us-east-2:123456789012:stateMachine:STNO-StateMachine",
    "detail": {
        "changed-tag-keys": ["TgwPeer"],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version-timestamp": 1646015600370.0,
        "version": 50.0,
        "tags": {
            "TgwPeer": "tgw-010101010abababab_us-east-1/tgw-010101011abababab_us-east-2",
            "Name": "STNO-TGW-us-east-1",
        },
    },
    "source": "aws.tag",
}


@pytest.mark.TDD
class TestValidateTag:
    """TDD test class for tgw_peering_helper validate-tag function"""

    TEST_TAG_EVENT = deepcopy(EC2_TAG_CHANGE_EVENT)

    def test__success__valid_tag(self):
        """success tag with valid value"""
        validate_tag(event=self.TEST_TAG_EVENT)

    def test__success__invalid_tag(self):
        """fail if tag with invalid value"""
        self.TEST_TAG_EVENT["detail"]["tags"][
            "TgwPeer"
        ] = "tgw-010101010abababab-us-east-1"
        with pytest.raises(ValueError) as err:
            validate_tag(event=self.TEST_TAG_EVENT)
        assert str(err.value) == "INVALID_TAG"

    def test__fail__delete_tag(self):
        """fail if tag with value 'Delete'"""
        self.TEST_TAG_EVENT["detail"]["tags"]["TgwPeer"] = "Delete"
        with pytest.raises(ValueError) as err:
            validate_tag(event=self.TEST_TAG_EVENT)
        assert str(err.value) == "DELETE_TAG"

    def test__fail__empty_tag(self):
        """fail if tag value is empty_tag"""
        self.TEST_TAG_EVENT["detail"]["tags"]["TgwPeer"] = ""
        with pytest.raises(ValueError) as err:
            validate_tag(event=self.TEST_TAG_EVENT)
        assert str(err.value) == "EMPTY_TAG"

    def test__fail__tag_removed(self):
        """fail if tag removed from source"""
        del self.TEST_TAG_EVENT["detail"]["tags"]["TgwPeer"]
        with pytest.raises(KeyError):
            validate_tag(event=self.TEST_TAG_EVENT)


@pytest.mark.BDD
class TestTagEventRouter:
    """BDD test class for tgw_peering_helper tag-event-router function"""

    # mock setup
    tag_value = EC2_TAG_CHANGE_EVENT["detail"]["tags"]["TgwPeer"]
    peers = tag_value.split("/")

    peer1 = TGWPeer(
        transit_gateway=peers[0].split("_")[0],
        aws_region=peers[0].split("_")[1],
    )
    peer1_with_attachment: TGWPeer = deepcopy(peer1)
    peer1_with_attachment.attachment_id = "attach-1"

    peer2 = TGWPeer(
        transit_gateway=peers[1].split("_")[0],
        aws_region=peers[1].split("_")[1],
    )
    peer2_with_attachment: TGWPeer = deepcopy(peer2)
    peer2_with_attachment.attachment_id = "attach-2"

    def test__success(self, mocker):
        """success, no peering attachments exists, 2 new peering attachments created and accepted"""
        m1 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.delete_tgw_peering_attachment"
        )
        mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.get_tgw_peers",
            side_effect=[
                [],
                [self.peer1_with_attachment, self.peer2_with_attachment],
            ],
        )
        m2 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.create_tgw_peering_attachment",
        )
        m3 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.accept_tgw_peering_attachment",
        )
        asyncio.run(tag_event_router(self.tag_value))

        assert m1.call_count == 0

        assert m2.call_count == 2  # create 2 peering attachments
        m2.assert_any_call(tgw_id=os.environ.get("TGW_ID"), peer=self.peer1)
        m2.assert_any_call(tgw_id=os.environ.get("TGW_ID"), peer=self.peer2)

        assert (
            m3.call_count == 2
        )  # 2 peering attachments created, accept 2 peering attachments
        m3.assert_any_call(self.peer1_with_attachment)
        m3.assert_any_call(self.peer2_with_attachment)

    def test__success_delete_tag(self, mocker):
        """success, delete tag found, delete 2 peering attachments"""
        m1 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.delete_tgw_peering_attachment"
        )
        mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.get_tgw_peers",
            return_value=[
                self.peer1_with_attachment,
                self.peer2_with_attachment,
            ],
        )

        asyncio.run(tag_event_router("delete"))
        assert m1.call_count == 2
        m1.assert_any_call(self.peer1_with_attachment)
        m1.assert_any_call(self.peer2_with_attachment)

    def test__success_crud(self, mocker):
        "success, create 1 new peering attachment, delete 1 old peering attachment"

        # mock new peer
        new_peer_tgw = "tgw-010101012abababab"
        new_peer_region = "us-west-1"
        new_peer_attachment = "attach-3"
        new_peer = TGWPeer(
            transit_gateway=new_peer_tgw,
            aws_region=new_peer_region,
        )
        new_peer_with_attachment: TGWPeer = deepcopy(new_peer)
        new_peer_with_attachment.attachment_id = new_peer_attachment

        updated_tag_value = (
            self.peers[0] + "/" + new_peer_tgw + "_" + new_peer_region
        )

        mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.get_tgw_peers",
            side_effect=[
                [self.peer1_with_attachment, self.peer2_with_attachment],
                [new_peer_with_attachment],
            ],
        )
        m1 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.create_tgw_peering_attachment"
        )
        m2 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.delete_tgw_peering_attachment",
            side_effect=KeyError(
                "delete_tgw_peering_attachment raises key error"
            ),
        )
        m3 = mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.accept_tgw_peering_attachment"
        )

        asyncio.run(tag_event_router(updated_tag_value))
        assert m1.call_count == 1
        m1.assert_called_once_with(
            tgw_id=os.environ.get("TGW_ID"), peer=new_peer
        )
        m2.assert_called_once_with(self.peer2_with_attachment)
        m3.assert_called_once_with(new_peer_with_attachment)

    def test__fail__get_tgw_peers(self, mocker):
        """fail with get_tgw_peers throwing client error"""
        mocker.patch(
            "tgw_peering_attachment.lib.transit_gateway.TGWPeering.get_tgw_peers",
            side_effect=Exception("error raised from get_tgw_peers"),
        )

        with pytest.raises(Exception) as err:
            asyncio.run(tag_event_router(""))
        assert str(err.value) == "error raised from get_tgw_peers"
