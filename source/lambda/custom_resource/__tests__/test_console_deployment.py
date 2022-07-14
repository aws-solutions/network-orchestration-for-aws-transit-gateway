# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource helper test module"""

import json
import unittest
from os import environ, path
from unittest.mock import mock_open

import pytest

from custom_resource.lib.console_deployment import ConsoleDeployment

RESOURCE_PROPERTIES = {
    "SrcBucket": "solutionBucker",
    "SrcPath": "stno/version",
    "ConsoleBucket": "myConsoleBucket",
    "AwsUserPoolsId": "myUserPoolId",
    "AwsUserPoolsWebClientId": "myWebClient",
    "AwsCognitoIdentityPoolId": "myCognitoIdp",
    "AwsAppsyncGraphqlEndpoint": "myAppSyncEndpoint",
    "AwsContentDeliveryBucket": "myCDNBucket",
    "AwsContentDeliveryUrl": "muCDNUrl",
    "AwsCognitoDomainPrefix": ""
}
CREATE_CONSOLE_DEPLOY = {
    "RequestType": "Create",
    "ResourceProperties": RESOURCE_PROPERTIES,
}


class TestClassConsoleDeploy(unittest.TestCase):

    def test__delete_event(self):
        """delete, does nothing"""
        # GIVEN
        console_deployment = ConsoleDeployment({}, mock_open, path.exists)

        # WHEN
        return_value = console_deployment.deploy({"RequestType": "Delete", "ResourceProperties": RESOURCE_PROPERTIES, })

        # THEN
        assert return_value == False

    def test__failed__file_not_found(self):
        """failed, manifest file not found"""
        # GIVEN
        console_deployment = ConsoleDeployment({}, mock_open, path.exists)

        # WHEN
        with pytest.raises(FileNotFoundError) as err:
            console_deployment.deploy(CREATE_CONSOLE_DEPLOY)

            # THEN
            assert str(err.value) == "console manifest file not found"

    def test__success(self):
        """success, console deploy"""
        # GIVEN
        environ["AWS_REGION"] = "my-region"

        class MockClient:
            def __init__(self):
                self.put_object_calls = 0
                self.copy_object_calls = 0

            def copy_object(self, **kwargs):
                self.copy_object_calls = self.copy_object_calls + 1

            def put_object(self, **kwargs):
                self.put_object_calls = self.put_object_calls + 1

        files = ["ui_file_1", "ui_file_2", "ui_file_3"]

        def exists_fn(_): return True

        open_fn = mock_open(read_data=json.dumps({"files": files}))

        client = MockClient()
        console_deployment = ConsoleDeployment(client, open_fn, exists_fn)

        # WHEN
        console_deployment.deploy(CREATE_CONSOLE_DEPLOY)

        # THEN
        assert client.put_object_calls == 1
        assert client.copy_object_calls == 3
