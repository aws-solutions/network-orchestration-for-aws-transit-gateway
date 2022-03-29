# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""CloudWatch Events test module"""

import os
import re
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from moto.events import mock_events
from custom_resource.lib.cloudwatch_events import CloudWatchEvents


@pytest.mark.TDD
@mock_events
class TestClassPutPermission:
    """TDD test class for CloudWatch Events put permission calls"""

    wrong_principal = "testprincipal"
    correct_principal = "123456789012"
    event_bus_name = "my-event-bus"

    def test__success(self):
        """success"""
        cwe = CloudWatchEvents()
        cwe.cwe_client.create_event_bus(Name=self.event_bus_name)
        cwe.put_permission(self.correct_principal, self.event_bus_name)
        cwe.cwe_client.delete_event_bus(Name=self.event_bus_name)  # clean-up

    def test__fail__resource_not_found(self):
        """fail with ResourceNotFoundException"""
        cwe = CloudWatchEvents()
        with pytest.raises(cwe.cwe_client.exceptions.ResourceNotFoundException):
            cwe.put_permission(self.correct_principal, self.event_bus_name)

    def test__fail__client_error(self):
        """fail with InvalidParameterValue"""
        cwe = CloudWatchEvents()
        cwe.cwe_client.create_event_bus(Name=self.event_bus_name)
        with pytest.raises(ClientError) as err:
            cwe.put_permission(self.wrong_principal, self.event_bus_name)
        assert err.value.response["Error"]["Code"] == "InvalidParameterValue"
        cwe.cwe_client.delete_event_bus(Name=self.event_bus_name)  # clean-up


@pytest.mark.TDD
@mock_events
class TestClassRemovePermission:
    """TDD test class for CloudWatch Events remove permission calls"""

    correct_principal = "123456789012"
    statement_id = "my-statement-01"
    event_bus_name = "my-event-bus"

    def test__success(self):
        """success"""
        cwe = CloudWatchEvents()
        cwe.cwe_client.create_event_bus(Name=self.event_bus_name)  # mock setup
        cwe.put_permission(self.correct_principal, self.event_bus_name)
        cwe.remove_permission(self.statement_id, self.event_bus_name)
        cwe.cwe_client.delete_event_bus(Name=self.event_bus_name)  # clean-up

    def test__fail__resource_not_found_eventbus(self):
        """fail with ResourceNotFoundException"""
        cwe = CloudWatchEvents()
        assert (
            cwe.remove_permission(self.statement_id, self.event_bus_name)
            is None
        )

    def test__fail__resource_not_found_policy(self):
        """fail with ResourceNotFoundException"""
        cwe = CloudWatchEvents()
        cwe.cwe_client.create_event_bus(Name=self.event_bus_name)
        assert (
            cwe.remove_permission("my-statement-02", self.event_bus_name)
            is None
        )
        cwe.cwe_client.delete_event_bus(Name=self.event_bus_name)  # clean-up

    def test__fail__client_error(self):
        """fail with ClientError"""
        cwe = CloudWatchEvents()
        stubber = Stubber(cwe.cwe_client)
        stubber.add_client_error(
            "remove_permission",
            service_error_code="InternalException",
            service_message="this is test error",
        )
        stubber.activate()
        with pytest.raises(ClientError):
            cwe.remove_permission(self.statement_id, self.event_bus_name)
        stubber.deactivate()


@pytest.mark.TDD
@mock_events
class TestClassDescribe:
    """TDD test class for CloudWatch Events describe calls"""

    event_bus_name = "my-event-bus"

    def test__success(self):
        """success"""
        cwe = CloudWatchEvents()
        cwe.cwe_client.create_event_bus(Name=self.event_bus_name)
        resp = cwe.describe_event_bus(event_bus_name=self.event_bus_name)
        assert resp["Name"] == self.event_bus_name
        _region = os.environ.get("AWS_DEFAULT_REGION")
        assert re.match(
            fr"(arn:aws:events:{_region}:)\d{{12}}:(event-bus/{self.event_bus_name})",
            resp["Arn"],
        )
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        cwe.cwe_client.delete_event_bus(Name=self.event_bus_name)  # clean-up

    def test__fail__resource_not_found(self):
        """fail with ResourceNotFoundException"""
        cwe = CloudWatchEvents()
        with pytest.raises(cwe.cwe_client.exceptions.ResourceNotFoundException):
            cwe.describe_event_bus(event_bus_name=self.event_bus_name)
