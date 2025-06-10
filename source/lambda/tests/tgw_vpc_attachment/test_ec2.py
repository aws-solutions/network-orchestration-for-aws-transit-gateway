# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

import os

from botocore.stub import Stubber

from solution.tgw_vpc_attachment.lib.clients.ec2 import EC2

os.environ["USER_AGENT_STRING"] = ""


def test_create_tags_batch_success(mocker):
    ec2 = EC2()
    client_stubber = Stubber(ec2.ec2_client)
    resource_id = "1234"
    response = {}
    tags_list = []
    expected_params = {"Resources": [resource_id], "Tags": tags_list}

    log_message = "Successfully tagged resource id 1234 with list of tags []"
    spy_logger = mocker.spy(ec2.logger, "debug")
    client_stubber.add_response("create_tags", response, expected_params)
    client_stubber.activate()
    ec2.create_tags_batch(resource_id, tags_list)
    spy_logger.assert_called_with(log_message)

def test_create_tgw_attachment_with_app_registry_tags():
    #  Arrange
    ec2 = EC2()
    ec2_client_stub = Stubber(ec2.ec2_client)

    tgw_id = "my_tgw"
    vpc_id = "my_vpc_id"
    subnet_id = "my_subnet"
    os.environ["APPLICATION_TAG_KEY"] = "awsApplication"
    os.environ["APPLICATION_TAG_VALUE"] = "myApp"
    expected_params = {
        "SubnetIds": [subnet_id],
        "TransitGatewayId": tgw_id,
        "VpcId": vpc_id,
        "TagSpecifications": [
            {
                "ResourceType": "transit-gateway-attachment",
                "Tags": [
                    {
                        "Key": os.getenv("APPLICATION_TAG_KEY"),
                        "Value": os.getenv("APPLICATION_TAG_VALUE")
                    }
                ]
            }
        ]
    }

    ec2_client_stub.add_response("create_transit_gateway_vpc_attachment", {}, expected_params)
    ec2_client_stub.activate()

    # Act/Assert
    with ec2_client_stub:
        ec2.create_transit_gateway_vpc_attachment(tgw_id, vpc_id, subnet_id)
        ec2_client_stub.assert_no_pending_responses()