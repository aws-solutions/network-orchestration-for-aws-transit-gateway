# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""
import os

os.environ["USER_AGENT_STRING"] = ""
from tgw_vpc_attachment.lib.clients.organizations import Organizations
from botocore.stub import Stubber


def test_get_account_name():
    organization = Organizations()
    account_id = "12345"
    client_stubber = Stubber(organization.org_client)
    response = {"Account": {"Name": "Test"}}
    expected_params = {"AccountId": account_id}
    client_stubber.add_response("describe_account", response, expected_params)
    client_stubber.activate()
    response = organization.get_account_name(account_id)
    assert response == "Test"


def test_get_account_name_exception():
    organization = Organizations()
    account_id = "12345"
    client_stubber = Stubber(organization.org_client)
    client_stubber.add_client_error("describe_account", "Invalid_request")
    client_stubber.activate()
    response = organization.get_account_name(account_id)
    assert response is None


def test_get_ou_name():
    organization = Organizations()
    ou_id = "12345"
    client_stubber = Stubber(organization.org_client)
    response = {"OrganizationalUnit": {"Name": "Test_OU_Name"}}
    expected_params = {"OrganizationalUnitId": ou_id}
    client_stubber.add_response(
        "describe_organizational_unit", response, expected_params
    )
    client_stubber.activate()
    response = organization.get_ou_name(ou_id)
    assert response == "Test_OU_Name"


def test_get_ou_name_exception():
    organization = Organizations()
    ou_id = "12345"
    client_stubber = Stubber(organization.org_client)
    client_stubber.add_client_error(
        "describe_organizational_unit", "Invalid_request"
    )
    client_stubber.activate()
    response = organization.get_ou_name(ou_id)
    assert response is None


def test_get_ou_path_root():
    organization = Organizations()
    account_id = "12345"
    client_stubber = Stubber(organization.org_client)
    response = {
        "Parents": [
            {"Id": "test_id", "Type": "Root"},
        ]
    }
    expected_params = {"ChildId": account_id}
    client_stubber.add_response("list_parents", response, expected_params)
    client_stubber.activate()
    return_value = organization.get_ou_path(account_id)
    assert return_value == "Root/"


def test_get_ou_path(mocker):
    organization = Organizations()
    account_id_1 = "12345"
    mocker.patch.object(organization, "get_ou_name")
    organization.get_ou_name.return_value = "ou-name"
    client_stubber = Stubber(organization.org_client)
    response1 = {
        "Parents": [
            {"Id": "test_id_1", "Type": "ORGANIZATIONAL_UNIT"},
        ]
    }
    response2 = {
        "Parents": [
            {"Id": "test_id_2", "Type": "Root"},
        ]
    }
    expected_params1 = {"ChildId": account_id_1}
    expected_params2 = {"ChildId": "test_id_1"}

    client_stubber.add_response("list_parents", response1, expected_params1)
    client_stubber.add_response("list_parents", response2, expected_params2)

    client_stubber.activate()
    return_value = organization.get_ou_path(account_id_1)
    assert return_value == "Root/ou-name/"


def test_get_ou_path_exception(mocker):
    organization = Organizations()
    account_id = "12345"
    mocker.patch.object(organization, "get_ou_name")
    organization.get_ou_name.return_value = "ou-name"
    client_stubber = Stubber(organization.org_client)
    client_stubber.add_client_error("list_parents", "Invalid_request")
    client_stubber.activate()
    return_value = organization.get_ou_path(account_id)
    assert return_value is None
