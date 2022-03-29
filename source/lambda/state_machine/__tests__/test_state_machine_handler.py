# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

import os

os.environ["USER_AGENT_STRING"] = ""
from state_machine.state_machine_handler import TransitGateway, VPC


def test_update_event_with_ou_name(mocker):
    event = {"region": "us-east-1", "account": "1234"}
    vpc = VPC(event)

    mocker.patch.object(vpc.org_client, "get_account_name")
    mocker.patch.object(vpc.org_client, "get_ou_path")

    vpc.org_client.get_account_name.return_value = "test_name"
    vpc.org_client.get_ou_path.return_value = "Root/a/b/"
    vpc._update_event_with_ou_name()
    assert event.get("AccountOuPath") == "Root/a/b/"
    assert event.get("AccountName") == "test_name"


def test_update_event_with_ou_name_spoke(mocker):
    event = {"region": "us-east-1", "AWSSpokeAccountId": "111111"}
    vpc = VPC(event)

    mocker.patch.object(vpc.org_client, "get_account_name")
    mocker.patch.object(vpc.org_client, "get_ou_path")

    vpc.org_client.get_account_name.return_value = "test_name_spoke"
    vpc.org_client.get_ou_path.return_value = "Root/a/b/spoke"
    vpc._update_event_with_ou_name()
    assert event.get("AccountOuPath") == "Root/a/b/spoke"
    assert event.get("AccountName") == "test_name_spoke"
