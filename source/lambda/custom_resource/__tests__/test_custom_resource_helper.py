# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
from copy import deepcopy
from os import environ
from unittest.mock import Mock

import pytest
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from custom_resource.lib.custom_resource_helper import (
    cfn_handler,
    handle_cwe_permissions,
    handle_prefix,
    handle_metrics,
    start_state_machine,
    send,
)

logger = Logger(os.getenv('LOG_LEVEL'))
logger.setLevel("DEBUG")

# pylint:disable=no-self-use, invalid-name
# using classes for unit-test grouping and running tests with class node-ids
CFN_REQUEST_EVENT = {
    "RequestType": "Create",
    "ResponseURL": "http://pre-signed-S3-url-for-response",
    "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/MyStack/guid",
    "RequestId": "unique id for this create request",
    "ResourceType": "Custom::TestResource",
    "LogicalResourceId": "MyTestResource",
    "ResourceProperties": {"StackName": "MyStack", "List": ["1", "2", "3"]},
}

# cloudformation events for different sources
CREATE_UUID_REQUEST = deepcopy(CFN_REQUEST_EVENT)
CREATE_UUID_REQUEST["ResourceType"] = "Custom::CreateUUID"

CREATE_CWE_PERMISSIONS = deepcopy(CFN_REQUEST_EVENT)
CREATE_CWE_PERMISSIONS["ResourceType"] = "Custom::CWEventPermissions"

CREATE_CONSOLE_DEPLOY = deepcopy(CFN_REQUEST_EVENT)
CREATE_CONSOLE_DEPLOY["ResourceType"] = "Custom::ConsoleDeploy"

CREATE_PREFIX = deepcopy(CFN_REQUEST_EVENT)
CREATE_PREFIX["ResourceType"] = "Custom::GetPrefixListArns"

CREATE_METRICS = deepcopy(CFN_REQUEST_EVENT)
CREATE_METRICS["ResourceType"] = "Custom::SendCFNParameters"

context = Mock()
context.get_remaining_time_in_millis = Mock()
context.get_remaining_time_in_millis.return_value = 10000
context.log_stream_name = "sample-stream"


@pytest.mark.TDD
class TestClassCfnHandler:
    """TDD test class for custom_resource_helper cfn_handler function"""

    def test__success__create_uuid(self, mocker):
        """success, create uuid"""
        mock_uuid = {"UUID": "uuid_000111"}
        m1 = mocker.patch(
            "custom_resource.lib.custom_resource_helper.handle_uuid",
            return_value=mock_uuid,
        )
        m2 = mocker.patch("custom_resource.lib.custom_resource_helper.send")

        cfn_handler(CREATE_UUID_REQUEST, context)
        assert m1.call_count == 1
        assert m2.call_count == 1
        m2.assert_called_once_with(
            CREATE_UUID_REQUEST, context, "SUCCESS", mock_uuid, None
        )

    def test__failed__create_uuid(self, mocker):
        """success, create uuid"""
        error = "error in handle_uuid"
        m1 = mocker.patch(
            "custom_resource.lib.custom_resource_helper.handle_uuid",
            side_effect=Exception(error),
        )
        m2 = mocker.patch("custom_resource.lib.custom_resource_helper.send")

        cfn_handler(CREATE_UUID_REQUEST, context)
        assert m1.call_count == 1
        assert m2.call_count == 1
        m2.assert_called_once_with(
            CREATE_UUID_REQUEST,
            context,
            "FAILED",
            {},
            error,
        )

    def test__success__create_cwe_permissions(self, mocker):
        """success, create cwe event permissions"""
        m1 = mocker.patch(
            "custom_resource.lib.custom_resource_helper.handle_cwe_permissions",
        )
        m2 = mocker.patch("custom_resource.lib.custom_resource_helper.send")

        cfn_handler(CREATE_CWE_PERMISSIONS, context)
        assert m1.call_count == 1
        assert m2.call_count == 1
        m2.assert_called_once_with(
            CREATE_CWE_PERMISSIONS, context, "SUCCESS", {}, None
        )


@pytest.mark.BDD
class TestClassCWEPermissions:
    """BDD test class for custom_resource_helper handle_cwe_permissions"""

    event_bus_name = "sample-bus"
    principals = ["P1", "P2"]
    old_principals = ["P2", "P3"]
    CREATE_CWE_PERMISSIONS["ResourceProperties"] = {
        "EventBusName": event_bus_name,
        "Principals": principals,
    }
    CREATE_CWE_PERMISSIONS["OldResourceProperties"] = {
        "Principals": old_principals,
    }

    def test__success__create(self, mocker):
        """success, create cwe events permission"""
        m1 = mocker.patch(
            "custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission"
        )
        handle_cwe_permissions(CREATE_CWE_PERMISSIONS)
        assert m1.call_count == 2
        for principal in self.principals:
            m1.assert_any_call(principal, self.event_bus_name)

    def test__success__delete(self, mocker):
        """success, delete cwe events permissions"""
        CREATE_CWE_PERMISSIONS["RequestType"] = "Delete"
        m1 = mocker.patch(
            "custom_resource.lib.cloudwatch_events.CloudWatchEvents.remove_permission"
        )
        handle_cwe_permissions(CREATE_CWE_PERMISSIONS)
        assert m1.call_count == 2
        for principal in self.principals:
            m1.assert_any_call(principal, self.event_bus_name)

    def test__success__update(self, mocker):
        """success, delete cwe events permissions"""
        CREATE_CWE_PERMISSIONS["RequestType"] = "Update"
        m1 = mocker.patch(
            "custom_resource.lib.cloudwatch_events.CloudWatchEvents.remove_permission"
        )
        m2 = mocker.patch(
            "custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission"
        )
        delete_list = list(set(self.old_principals) - set(self.principals))

        handle_cwe_permissions(CREATE_CWE_PERMISSIONS)
        assert m1.call_count == 1
        for principal in delete_list:
            m1.assert_any_call(principal, self.event_bus_name)
        assert m2.call_count == 2
        for principal in self.principals:
            m2.assert_any_call(principal, self.event_bus_name)

    def test__fail(self, mocker):
        """fail, cwe events permission"""
        mocker.patch(
            "custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission",
            side_effect=Exception("put permission error"),
        )
        with pytest.raises(Exception):
            handle_cwe_permissions(CREATE_CWE_PERMISSIONS)


class TestClassPrefix:
    """TDD/BDD class for testing generating prefix list arns from prefix list"""

    @pytest.mark.TDD
    def test__fail__value_error(self):
        """fail, empty prefix list"""
        CREATE_PREFIX["ResourceProperties"] = {"PrefixListIds": ""}
        with pytest.raises(ValueError):
            handle_prefix(CREATE_PREFIX)

    @pytest.mark.BDD
    def test__success(self):
        """success"""
        prefix_list = "list-1,list-2"
        account_id = "myAccountID"
        environ["AWS_REGION"] = "my-region"
        CREATE_PREFIX["ResourceProperties"] = {
            "PrefixListIds": prefix_list,
            "AccountId": account_id,
        }
        prefix_list_arns = [
            f"arn:aws:ec2:{environ.get('AWS_REGION')}:{account_id}:prefix-list/list-1",
            f"arn:aws:ec2:{environ.get('AWS_REGION')}:{account_id}:prefix-list/list-2",
        ]
        assert handle_prefix(CREATE_PREFIX) == {
            "PrefixListArns": prefix_list_arns
        }


class TestClassMetrics:
    """TDD/BDD class for metrics handler functions"""

    CREATE_METRICS["ResourceProperties"] = {
        "Uuid": "my-uuid",
        "PrincipalType": "my-principal",
        "ApprovalNotification": "my-notification",
        "AuditTrailRetentionPeriod": "my-retention",
        "DefaultRoute": "my-default-route",
        "CreatedNewTransitGateway": "Yes",
    }
    properties = CREATE_METRICS["ResourceProperties"]
    environ["AWS_REGION"] = "my-region"

    @pytest.mark.TDD
    def test__success__no_metric(self, mocker):
        """success, metric not sent when flag set to no"""
        environ["SEND_METRIC"] = "No"
        m1 = mocker.patch("custom_resource.lib.custom_resource_helper.send")
        handle_metrics(CREATE_METRICS)
        assert m1.call_count == 0

    @pytest.mark.BDD
    def test__success(self, mocker):
        """success, metric sent"""
        environ["SEND_METRIC"] = "Yes"
        environ["SOLUTION_ID"] = "SO-ID"
        environ["METRICS_ENDPOINT"] = "https://endpoint"
        data = {
            "PrincipalType": self.properties.get("PrincipalType"),
            "ApprovalNotificationFlag": self.properties.get(
                "ApprovalNotification"
            ),
            "AuditTrailRetentionPeriod": self.properties.get(
                "AuditTrailRetentionPeriod"
            ),
            "DefaultRoute": self.properties.get("DefaultRoute"),
            "Region": environ.get("AWS_REGION"),
            "SolutionVersion": environ.get("SOLUTION_VERSION"),
            "Event": f"Solution_{CREATE_METRICS['RequestType']}",
            "CreatedNewTransitGateway": self.properties.get(
                "CreatedNewTransitGateway"
            ),
        }

        # successfully sent
        m1 = mocker.patch(
            "custom_resource.lib.custom_resource_helper.send_metrics",
            return_value="success",
        )
        handle_metrics(CREATE_METRICS)
        m1.assert_any_call(
            uuid=self.properties.get("Uuid"),
            data=data,
            solution_id=environ.get("SOLUTION_ID"),
            url=environ.get("METRICS_ENDPOINT"),
        )

        # warning, failure in send
        mocker.patch(
            "custom_resource.lib.custom_resource_helper.send_metrics",
            side_effect=Exception("error sending metrics"),
        )
        handle_metrics(CREATE_METRICS)


@pytest.mark.TDD
class TestClassTriggerSM:
    """TDD test class to handle state machine execution"""

    def test__success__fail(self, mocker):
        """success and exceptions for state machine execution"""

        # success
        mocker.patch(
            "custom_resource.lib.step_functions.StepFunctions.trigger_state_machine"
        )
        context = LambdaContext()
        context._invoked_function_arn = "abc:abc:abc:abc:abc:abc:abc"
        start_state_machine({}, context)

        # failed
        mocker.patch(
            "custom_resource.lib.step_functions.StepFunctions.trigger_state_machine",
            side_effect=Exception("error triggering state machine"),
        )
        with pytest.raises(Exception):
            start_state_machine({}, context)


@pytest.mark.TDD
class TestClassSendCfnResponse:
    """TDD test class for send cfn response function"""

    def test__success__fail(self, mocker):
        """success and exceptions for state machine execution"""

        # success
        m1 = mocker.patch(
            "requests.put",
        )
        send(
            event=CFN_REQUEST_EVENT,
            context=context,
            response_status="SUCCESS",
            response_data={},
        )

        # failed
        m1.side_effect = Exception("error triggering state machine")
        with pytest.raises(Exception) as err:
            send(
                event=CFN_REQUEST_EVENT,
                context=context,
                response_status="SUCCESS",
                response_data={},
            )
        assert str(err.value) == "error triggering state machine"


class AWSLambdaContext:
    def __init__(self):
        self.invoked_function_arn = "abc:abc:abc:abc:abc:abc:abc"
