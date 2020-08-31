import pytest
from os import environ
from lib.logger import Logger
import tgw_peering_attachment_handler as tgw_pa

logger = Logger('info')

environ['TGW_PEERING_TAG_PREFIX'] = "TgwPeer"
environ['TGW_PEERING_TAG_DELIMITER'] = "Colon (:)"
environ['AWS_REGION'] = 'us-east-1'

peering_attachment_not_found = {
    'TgwPeeringAttachmentExist': 'No',
    'TgwPeeringAttachmentState': 'does-not-exist'
}

create_event = {
  "version": "0",
  "id": "748c49490",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "11111111",
  "time": "2020-07-28T13:43:55Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ec2:us-east-1:11111111:transit-gateway/tgw-0a899af2"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-2:2"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": 59,
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-1:11111111:stack/stno-v2-va-7/e72317d0-c1f0-11ea-b90c-12cf4a8c2bc2",
      "TgwPeer:us-east-2:2": "tgw-031cdc5",
      "Name": "STNO-TGW-us-east-1"
    }
  },
  "params": {
    "MethodName": "get_transit_gateway_peering_attachment_id"
  },
  "PeeringTag": "TgwPeer:us-east-2:2",
  "IsTgwPeeringTagEvent": "Yes",
  "RequestType": "Create",
  "TgwId": "tgw-0a899af2",
  "PeerTgwId": "tgw-031cdc5",
  "PeerRegion": "us-east-2",
  "PeerAccountId": "11111111"
}

create_second_peer_attachment_same_region = {
  "version": "0",
  "id": "2512fc44",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "11111111",
  "time": "2020-07-28T14:06:00Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ec2:us-east-1:11111111:transit-gateway/tgw-0a899af2"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-2"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": 60,
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-1:11111111:stack/stno-v2-va-7/e72317d0-c1f0-11ea-b90c-12cf4a8c2bc2",
      "TgwPeer:us-east-2": "tgw-0c7e4fe",
      "TgwPeer:us-east-2:2": "tgw-031cdc5",
      "Name": "STNO-TGW-us-east-1"
    }
  },
  "params": {
    "MethodName": "get_transit_gateway_peering_attachment_id"
  },
  "PeeringTag": "TgwPeer:us-east-2",
  "IsTgwPeeringTagEvent": "Yes",
  "RequestType": "Create",
  "TgwId": "tgw-0a899af2",
  "PeerTgwId": "tgw-0c7e4fe",
  "PeerRegion": "us-east-2",
  "PeerAccountId": "11111111"
}

delete_event = {
  "version": "0",
  "id": "e5816e33",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "11111111",
  "time": "2020-07-28T14:21:00Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ec2:us-east-1:11111111:transit-gateway/tgw-0a899af2"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-2:2"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": 61,
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-1:11111111:stack/stno-v2-va-7/e72317d0-c1f0-11ea-b90c-12cf4a8c2bc2",
      "TgwPeer:us-east-2": "tgw-0c7e4fe",
      "Name": "STNO-TGW-us-east-1"
    }
  },
  "params": {
    "MethodName": "get_transit_gateway_peering_attachment_id"
  },
  "PeeringTag": "TgwPeer:us-east-2:2",
  "IsTgwPeeringTagEvent": "Yes",
  "RequestType": "Delete",
  "TgwId": "tgw-0a899af2",
  "PeerTgwId": "None",
  "PeerRegion": "us-east-2",
  "PeerAccountId": "11111111"
}

delete_last_attachment_event = {
  "version": "0",
  "id": "bbcafe51",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "11111111",
  "time": "2020-07-28T14:41:10Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ec2:us-east-1:11111111:transit-gateway/tgw-0a899af2"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-2"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": 62,
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-1:11111111:stack/stno-v2-va-7/e72317d0-c1f0-11ea-b90c-12cf4a8c2bc2",
      "Name": "STNO-TGW-us-east-1"
    }
  },
  "params": {
    "MethodName": "get_transit_gateway_peering_attachment_id"
  },
  "PeeringTag": "TgwPeer:us-east-2",
  "IsTgwPeeringTagEvent": "Yes",
  "RequestType": "Delete",
  "TgwId": "tgw-0a899af2",
  "PeerTgwId": "None",
  "PeerRegion": "us-east-2",
  "PeerAccountId": "11111111"
}

no_existing_attachment_response = []

existing_attachment_response = [
    {
        "TransitGatewayAttachmentId": "tgw-attach-0f3c8530",
        "RequesterTgwInfo": {
            "TransitGatewayId": "tgw-0a899af2",
            "OwnerId": "11111111",
            "Region": "us-east-1"
        },
        "AccepterTgwInfo": {
            "TransitGatewayId": "tgw-031cdc5",
            "OwnerId": "11111111",
            "Region": "us-east-2"
        },
        "Status": {
            "Code": "available",
            "Message": "Available"
        },
        "State": "available",
        "CreationTime": "2020-07-28T13:43:58+00:00",
        "Tags": []
    }
]

last_attachment_response = [
    {
        "TransitGatewayAttachmentId": "tgw-attach-099b887",
        "RequesterTgwInfo": {
            "TransitGatewayId": "tgw-0a899af2",
            "OwnerId": "11111111",
            "Region": "us-east-1"
        },
        "AccepterTgwInfo": {
            "TransitGatewayId": "tgw-0c7e4fe",
            "OwnerId": "11111111",
            "Region": "us-east-2"
        },
        "Status": {
            "Code": "available",
            "Message": "Available"
        },
        "State": "available",
        "CreationTime": "2020-07-28T14:06:05+00:00",
        "Tags": []
    }
]

two_existing_attachment_response = [
    {
        "TransitGatewayAttachmentId": "tgw-attach-099b887",
        "RequesterTgwInfo": {
            "TransitGatewayId": "tgw-0a899af2",
            "OwnerId": "11111111",
            "Region": "us-east-1"
        },
        "AccepterTgwInfo": {
            "TransitGatewayId": "tgw-0c7e4fe",
            "OwnerId": "11111111",
            "Region": "us-east-2"
        },
        "Status": {
            "Code": "available",
            "Message": "Available"
        },
        "State": "available",
        "CreationTime": "2020-07-28T14:06:05+00:00",
        "Tags": []
    },
    {
        "TransitGatewayAttachmentId": "tgw-attach-0f3c8530",
        "RequesterTgwInfo": {
            "TransitGatewayId": "tgw-0a899af2",
            "OwnerId": "11111111",
            "Region": "us-east-1"
        },
        "AccepterTgwInfo": {
            "TransitGatewayId": "tgw-031cdc5",
            "OwnerId": "11111111",
            "Region": "us-east-2"
        },
        "Status": {
            "Code": "available",
            "Message": "Available"
        },
        "State": "available",
        "CreationTime": "2020-07-28T14:09:05+00:00",
        "Tags": []
    }
]


def test_create_new_attachment_event():
    tgw_client = tgw_pa.TgwTagEventHandler(create_event)
    tgw_client.tgw_peering_attachment_id_finder(no_existing_attachment_response,
                                                peering_attachment_not_found)
    logger.info(create_event)
    assert create_event.get('TgwPeeringAttachmentExist') == 'No'
    assert create_event.get('TgwPeeringAttachmentState') == 'does-not-exist'


def test_create_second_new_attachment_event():
    tgw_client = tgw_pa.TgwTagEventHandler(create_second_peer_attachment_same_region)
    tgw_client.tgw_peering_attachment_id_finder(existing_attachment_response,
                                                peering_attachment_not_found)
    logger.info(create_event)
    assert create_event.get('TgwPeeringAttachmentExist') == 'No'
    assert create_event.get('TgwPeeringAttachmentState') == 'does-not-exist'


def test_create_if_existing_attachment_event():
    tgw_client = tgw_pa.TgwTagEventHandler(create_event)
    tgw_client.tgw_peering_attachment_id_finder(existing_attachment_response,
                                                peering_attachment_not_found)
    logger.info(create_event)
    assert create_event.get('TgwPeeringAttachmentExist') == 'Yes'
    assert create_event.get('TgwPeeringAttachmentState') == 'available'
    assert create_event.get('TgwPeeringAttachmentId') == 'tgw-attach-0f3c8530'


# identify tgw attachment id in deletion workflow
def test_delete_second_attachment_event():
    tgw_client = tgw_pa.TgwTagEventHandler(delete_event)
    tgw_client.tgw_peering_attachment_id_finder(two_existing_attachment_response,
                                                peering_attachment_not_found)
    logger.info(delete_event)
    assert delete_event.get('TgwPeeringAttachmentExist') == 'Yes'
    assert delete_event.get('TgwPeeringAttachmentState') == 'available'
    assert delete_event.get('TgwPeeringAttachmentId') == 'tgw-attach-0f3c8530'


# identify tgw attachment id in deletion workflow
def test_delete_last_attachment_event():
    tgw_client = tgw_pa.TgwTagEventHandler(delete_last_attachment_event)
    tgw_client.tgw_peering_attachment_id_finder(last_attachment_response,
                                                peering_attachment_not_found)
    logger.info(delete_event)
    assert delete_last_attachment_event.get('TgwPeeringAttachmentExist') == 'Yes'
    assert delete_last_attachment_event.get('TgwPeeringAttachmentState') == 'available'
    assert delete_last_attachment_event.get('TgwPeeringAttachmentId') == 'tgw-attach-099b887'
