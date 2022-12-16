# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

import os

from botocore.stub import Stubber

from state_machine.lib.clients.ec2 import EC2

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


def test_create_tags_batch_exception(mocker):
    ec2 = EC2()
    client_stubber = Stubber(ec2.ec2_client)
    resource_id = 1234
    tags_list = []
    spy_logger = mocker.spy(ec2.logger, "exception")
    client_stubber.add_client_error("create_tags", "Invalid_request")
    client_stubber.activate()
    ec2.create_tags_batch(resource_id, tags_list)
    assert spy_logger.call_count == 2
