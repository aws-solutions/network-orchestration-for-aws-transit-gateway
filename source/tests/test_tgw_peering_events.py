import pytest
from os import environ
from lib.logger import Logger
from tgw_peering_attachment_handler import TgwTagEventModifier, \
    TgwTagEventHandler, lambda_handler

logger = Logger('info')

environ['TGW_PEERING_TAG_PREFIX'] = "TgwPeer"
environ['TGW_PEERING_TAG_DELIMITER'] = "Colon (:)"
environ['AWS_REGION'] = 'us-east-1'

create_event = {
    "version": "0",
    "id": "b981b7b4-0800-679c-5002-d77042b7b052",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "1111111111",
    "time": "2020-06-25T13:42:10Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "TgwPeer:us-east-1:1"
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 3.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111"
                             ":stack/StackSet-STNO-hub-test-1-400fcc66-5aac"
                             "-4644-b13b-5a0d8f20bba5/ad0d5450-f425-11e9-9550"
                             "-0afb0832a490",
            "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    }
}

create_event_multiple_tags = {
    "version": "0",
    "id": "b981b7b4-0800-679c-5002-d77042b7b052",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "1111111111",
    "time": "2020-06-25T13:42:10Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "test3",
            "test",
            "TgwPeer:us-east-1:1"
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 3.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111"
                             ":stack/StackSet-STNO-hub-test-1-400fcc66-5aac"
                             "-4644-b13b-5a0d8f20bba5/ad0d5450-f425-11e9-9550"
                             "-0afb0832a490",
            "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
            "test3": "value3",
            "test": "value",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    }
}

create_event_multiple_valid_tags = {
    "version": "0",
    "id": "b981b7b4-0800-679c-5002-d77042b7b052",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "1111111111",
    "time": "2020-06-25T13:42:10Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "test3",
            "test",
            "TgwPeer:us-east-1:1",
            "TgwPeer:us-west-1:1"
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 3.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111"
                             ":stack/StackSet-STNO-hub-test-1-400fcc66-5aac"
                             "-4644-b13b-5a0d8f20bba5/ad0d5450-f425-11e9-9550"
                             "-0afb0832a490",
            "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
            "TgwPeer:us-west-1:1": "tgw-random-value",
            "test3": "value3",
            "test": "value",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    }
}


invalid_tag_event = {
    "version": "0",
    "id": "b981b7b4-0800-679c-5002-d77042b7b052",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "1111111111",
    "time": "2020-06-25T13:42:10Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "InvalidTag:us-east-1:1"  # invalid tag and region name
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 3.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111",
            "InvalidTag:us-east-1:1": "tgw-qwerty1234567",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    }
}

delete_event = {
    "version": "0",
    "id": "939c9bb0-6e57-9d18-c1a6-43df850f8565",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "3333",
    "time": "2020-06-25T13:44:05Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:3333:transit-gateway/tgw"
        "-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "TgwPeer:us-east-1:1"
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 4.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:3333"
                             ":stack/StackSet-STNO-hub-test-1-400fcc66-5aac"
                             "-4644-b13b-5a0d8f20bba5/ad0d5450-f425-11e9-9550"
                             "-0afb0832a490",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    }
}

delete_event_multiple_tags = {
  "version": "0",
  "id": "2ea8e2bd-3594-1559-23bb-1df1035cc8ca",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "1111111111",
  "time": "2020-07-09T22:21:50Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ec2:us-east-1:1111111111:transit-gateway/tgw-0a899af2f15f4596a"
  ],
  "detail": {
    "changed-tag-keys": [
      "test3",
      "test",
      "TgwPeer:us-east-2"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": 13,
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-1:1111111111:stack/stno-v2-va-7/e72317d0-c1f0-11ea-b90c-12cf4a8c2bc2",
      "Name": "STNO-TGW-us-east-1"
    }
  }
}

pre_existing_peering_data = {
    "version": "0",
    "id": "b981b7b4-0800-679c-5002-d77042b7b052",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "1111111111",
    "time": "2020-06-25T13:42:10Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
    ],
    "detail": {
        "changed-tag-keys": [
            "TgwPeer:us-east-1:1"
        ],
        "service": "ec2",
        "resource-type": "transit-gateway",
        "version": 3.0,
        "tags": {
            "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111"
                             ":stack/StackSet-STNO-hub-test-1-400fcc66-5aac"
                             "-4644-b13b-5a0d8f20bba5/ad0d5450-f425-11e9-9550"
                             "-0afb0832a490",
            "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
            "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
        }
    },
    "RequestType": "Create",
    "TgwId": "tgw-x1v2b3m35791",
    "PeerTgwId": "tgw-p2i5y6re0987654",
    "PeerRegion": "us-east-2",
    "PeerAccountId": "222222222"
}

event_with_method_name = {
  "version": "0",
  "id": "b981b7b4-0800-679c-5002-d77042b7b052",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "1111111111",
  "time": "2020-06-25T13:42:10Z",
  "region": "us-east-2",
  "resources": [
    "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-1:1"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": "3.0",
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111",
      "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
      "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
    }
  },
  "params": {
    "MethodName": "get_processed_tagging_event"
  }
}

event_with_invalid_method_name = {
  "version": "0",
  "id": "b981b7b4-0800-679c-5002-d77042b7b052",
  "detail-type": "Tag Change on Resource",
  "source": "aws.tag",
  "account": "1111111111",
  "time": "2020-06-25T13:42:10Z",
  "region": "us-east-2",
  "resources": [
    "arn:aws:ec2:us-east-2:1111111111:transit-gateway/tgw-0c7e4fe1e731b84d5"
  ],
  "detail": {
    "changed-tag-keys": [
      "TgwPeer:us-east-1:1"
    ],
    "service": "ec2",
    "resource-type": "transit-gateway",
    "version": "3.0",
    "tags": {
      "AWS Solutions": "arn:aws:cloudformation:us-east-2:1111111111",
      "TgwPeer:us-east-1:1": "tgw-qwerty1234567",
      "Name": "AWS Serverless Transit Network Orchestrator - us-east-2"
    }
  },
  "params": {
    "MethodName": "invalid_method_name"
  }
}


def test_valid_tgw_tag_event():
    tgw_event_modifier_object = TgwTagEventModifier(create_event)
    is_valid_event = tgw_event_modifier_object.is_valid_tagging_event()
    assert is_valid_event is True


def test_bad_tag_event():
    tgw_event_modifier_object = TgwTagEventModifier(invalid_tag_event)
    is_valid_event = tgw_event_modifier_object.is_valid_tagging_event()
    assert is_valid_event is False


def test_get_peer_region():
    tgw_event_modifier_object = TgwTagEventModifier(create_event)
    peer_region = tgw_event_modifier_object._get_peer_region()
    assert peer_region == 'us-east-1'


def test_adding_create_request_type():
    event_handler = TgwTagEventHandler(create_event)
    returned_event = event_handler.get_processed_tagging_event()
    assert returned_event.get('RequestType') == "Create"


def test_adding_delete_request_type():
    event_handler = TgwTagEventHandler(delete_event)
    returned_event = event_handler.get_processed_tagging_event()
    assert returned_event.get('RequestType') == "Delete"


def test_get_peering_data_event():
    event_handler = TgwTagEventHandler(create_event)
    returned_event = event_handler.get_processed_tagging_event()
    logger.info(returned_event)
    assert returned_event.get('TgwId') == "tgw-0c7e4fe1e731b84d5"
    assert returned_event.get('PeerTgwId') == "tgw-qwerty1234567"
    assert returned_event.get('PeerRegion') == "us-east-1"
    assert returned_event.get('PeerAccountId') == "1111111111"


def test_existing_peering_data_event():
    event_handler = TgwTagEventHandler(pre_existing_peering_data)
    returned_event = event_handler.get_processed_tagging_event()
    logger.info(returned_event)
    assert returned_event.get('TgwId') == "tgw-x1v2b3m35791"
    assert returned_event.get('PeerTgwId') == "tgw-p2i5y6re0987654"
    assert returned_event.get('PeerRegion') == "us-east-2"
    assert returned_event.get('PeerAccountId') == "222222222"


def test_method_name_as_string():
    context = {}
    returned_event = lambda_handler(event_with_method_name, context)
    logger.info(returned_event)
    assert type(returned_event) is dict


def test_invalid_method_name_as_string():
    context = {}
    with pytest.raises(NotImplementedError, match=r".*is not a valid method."):
        lambda_handler(event_with_invalid_method_name, context)


def test_tag_list_reduction_create_multiple_tags():
    event_handler = TgwTagEventHandler(create_event_multiple_tags)
    returned_event = event_handler.get_processed_tagging_event()
    assert returned_event.get('PeeringTag').startswith(environ.get(
        'TGW_PEERING_TAG_PREFIX'))


def test_tag_list_reduction_create_multiple_valid_tags():
    event_handler = TgwTagEventHandler(create_event_multiple_valid_tags)
    with pytest.raises(KeyError, match=r"STNO Error: Please delete and "
                                       r"add following tag keys individually"):
        event_handler.get_processed_tagging_event()


def test_tag_list_reduction_delete_multiple_tags():
    event_handler = TgwTagEventHandler(delete_event_multiple_tags)
    returned_event = event_handler.get_processed_tagging_event()
    assert returned_event.get('PeeringTag').startswith(environ.get(
        'TGW_PEERING_TAG_PREFIX'))
