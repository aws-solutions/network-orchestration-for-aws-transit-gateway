# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
from copy import deepcopy
from os import environ
from unittest.mock import Mock, patch
from datetime import datetime, timezone

import pytest
import boto3
from moto import mock_iam
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from solution.custom_resource.lib.custom_resource_helper import (
    cfn_handler,
    handle_cwe_permissions,
    handle_prefix,
    handle_metrics,
    start_state_machine,
    send,
    get_resource_type_details,
    create_service_linked_role,
    SERVICE_LINKED_ROLE_NAME
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
            "solution.custom_resource.lib.custom_resource_helper.handle_uuid",
            return_value=mock_uuid,
        )
        m2 = mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")

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
            "solution.custom_resource.lib.custom_resource_helper.handle_uuid",
            side_effect=Exception(error),
        )
        m2 = mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")

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
            "solution.custom_resource.lib.custom_resource_helper.handle_cwe_permissions",
        )
        m2 = mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")

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
            "solution.custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission"
        )
        handle_cwe_permissions(CREATE_CWE_PERMISSIONS)
        assert m1.call_count == 2
        for principal in self.principals:
            m1.assert_any_call(principal, self.event_bus_name)

    def test__success__update(self, mocker):
        """success, delete cwe events permissions"""
        CREATE_CWE_PERMISSIONS["RequestType"] = "Update"
        m1 = mocker.patch(
            "solution.custom_resource.lib.cloudwatch_events.CloudWatchEvents.remove_permission"
        )
        m2 = mocker.patch(
            "solution.custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission"
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
            "solution.custom_resource.lib.cloudwatch_events.CloudWatchEvents.put_permission",
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
        environ["PARTITION"] = "aws"
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
        "DeployWebUI": "Yes",
        "CreatedNewTransitGateway": "Yes",
    }
    properties = CREATE_METRICS["ResourceProperties"]
    environ["AWS_REGION"] = "my-region"

    @pytest.mark.BDD
    def test__success(self, mocker):
        """success, metric sent"""
        environ["SOLUTION_ID"] = "SO-ID"
        environ["METRICS_ENDPOINT"] = "https://endpoint"
        environ["SOLUTION_VERSION"] = "v1.0.0"
        
        # Mock CloudFormation client and response
        mock_cfn_client = mocker.patch("boto3.client")
        mock_cfn_instance = Mock()
        mock_cfn_client.return_value = mock_cfn_instance
        
        # Mock describe_stacks response
        creation_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_cfn_instance.describe_stacks.return_value = {
            'Stacks': [{
                'CreationTime': creation_time
            }]
        }
        
        data = {
            "event": {
                "type": "solution",
                "action": "create"
            },
            "solution": {
                "PrincipalType": self.properties.get("PrincipalType"),
                "ApprovalNotificationFlag": self.properties.get("ApprovalNotification"),
                "AuditTrailRetentionPeriod": self.properties.get("AuditTrailRetentionPeriod"),
                "DefaultRoute": self.properties.get("DefaultRoute"),
                "DeployWebUI": self.properties.get("DeployWebUI"),
                "Region": environ.get("AWS_REGION"),
                "CreatedNewTransitGateway": self.properties.get("CreatedNewTransitGateway"),
                "created_at": creation_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            },
            "version": environ.get("SOLUTION_VERSION")
        }

        # successfully sent
        m1 = mocker.patch(
            "solution.custom_resource.lib.custom_resource_helper.send_metrics",
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
            "solution.custom_resource.lib.custom_resource_helper.send_metrics",
            side_effect=Exception("error sending metrics"),
        )
        handle_metrics(CREATE_METRICS)


@pytest.mark.BDD
@mock_iam
class TestClassCreateServiceLinkedRole:
    """BDD class for testing creation of service linked role"""
    iam_client = boto3.client("iam")

    @staticmethod
    def _setup_aws_mocks(mocker):
        """Setup IAM client mock (no EC2 needed - IAM handles role-in-use validation)"""
        mock_boto = mocker.patch('boto3.client')
        mock_iam = Mock()
        mock_boto.return_value = mock_iam
        return {'iam': mock_iam}

    @staticmethod
    def _create_delete_event(physical_resource_id):
        """Create a delete event with specified PhysicalResourceId"""
        delete_event = deepcopy(CFN_REQUEST_EVENT)
        delete_event["RequestType"] = "Delete"
        delete_event["ResourceType"] = "Custom::CreateServiceLinkedRole"
        delete_event["PhysicalResourceId"] = physical_resource_id
        delete_event["ResourceProperties"] = {}
        return delete_event

    def test__create_when_not_exists(self, mocker):
        mock_clients = self._setup_aws_mocks(mocker)
        error_response = {'Error': {'Code': 'NoSuchEntity', 'Message': 'Role not found'}}
        mock_clients['iam'].get_role.side_effect = ClientError(error_response, 'GetRole')
        mock_clients['iam'].create_service_linked_role.return_value = {
            'Role': {'RoleName': SERVICE_LINKED_ROLE_NAME}
        }
        
        create_event = deepcopy(CFN_REQUEST_EVENT)
        create_event["ResourceType"] = "Custom::CreateServiceLinkedRole"
        create_event["ResourceProperties"] = {}
        
        resp = create_service_linked_role(create_event)
        
        assert resp["RoleName"] == SERVICE_LINKED_ROLE_NAME
        assert resp["PhysicalResourceId"] == SERVICE_LINKED_ROLE_NAME
        mock_clients['iam'].create_service_linked_role.assert_called_once()

    def test__skip_when_exists(self, mocker):
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].get_role.return_value = {'Role': {'RoleName': SERVICE_LINKED_ROLE_NAME}}
        
        create_event = deepcopy(CFN_REQUEST_EVENT)
        create_event["ResourceType"] = "Custom::CreateServiceLinkedRole"
        create_event["ResourceProperties"] = {}
        
        resp = create_service_linked_role(create_event)
        
        assert resp["RoleName"] == SERVICE_LINKED_ROLE_NAME
        assert resp["PhysicalResourceId"] == SERVICE_LINKED_ROLE_NAME

    def test__update_with_existing_role(self, mocker):
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].get_role.return_value = {'Role': {'RoleName': SERVICE_LINKED_ROLE_NAME}}
        
        update_event = deepcopy(CFN_REQUEST_EVENT)
        update_event["RequestType"] = "Update"
        update_event["ResourceType"] = "Custom::CreateServiceLinkedRole"
        update_event["ResourceProperties"] = {}
        
        resp = create_service_linked_role(update_event)
        
        assert resp["RoleName"] == SERVICE_LINKED_ROLE_NAME
        assert resp["PhysicalResourceId"] == SERVICE_LINKED_ROLE_NAME

    def test__delete_succeeds(self, mocker):
        """Test deletion completes successfully"""
        mocker.patch('time.sleep')
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].delete_service_linked_role.return_value = {'DeletionTaskId': 'task-123'}
        mock_clients['iam'].get_service_linked_role_deletion_status.return_value = {'Status': 'SUCCEEDED'}
        delete_event = self._create_delete_event(SERVICE_LINKED_ROLE_NAME)
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "True"

    def test__delete_when_role_already_deleted(self, mocker):
        """Test deletion handles already-deleted role gracefully"""
        mock_clients = self._setup_aws_mocks(mocker)
        error_response = {'Error': {'Code': 'NoSuchEntity', 'Message': 'Role not found'}}
        mock_clients['iam'].delete_service_linked_role.side_effect = ClientError(error_response, 'DeleteServiceLinkedRole')
        delete_event = self._create_delete_event(SERVICE_LINKED_ROLE_NAME)
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "True"

    def test__delete_role_in_use_returns_gracefully(self, mocker):
        """Test deletion handles role-in-use gracefully (IAM returns FAILED)"""
        mocker.patch('time.sleep')
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].delete_service_linked_role.return_value = {'DeletionTaskId': 'task-123'}
        mock_clients['iam'].get_service_linked_role_deletion_status.return_value = {
            'Status': 'FAILED',
            'Reason': {'Reason': 'Role is in use by Transit Gateway'}
        }
        delete_event = self._create_delete_event(SERVICE_LINKED_ROLE_NAME)
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "False"
        assert "Deletion failed" in resp["Reason"]

    def test__delete_task_disappears(self, mocker):
        """Test when deletion task disappears (NoSuchEntity) - treated as deleted"""
        mocker.patch('time.sleep')
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].delete_service_linked_role.return_value = {'DeletionTaskId': 'task-123'}
        error_response = {'Error': {'Code': 'NoSuchEntity', 'Message': 'Task not found'}}
        mock_clients['iam'].get_service_linked_role_deletion_status.side_effect = ClientError(error_response, 'GetServiceLinkedRoleDeletionStatus')
        delete_event = self._create_delete_event(SERVICE_LINKED_ROLE_NAME)
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "True"

    def test__delete_timeout(self, mocker):
        """Test when deletion times out after 60 seconds"""
        mocker.patch('time.sleep')
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].delete_service_linked_role.return_value = {'DeletionTaskId': 'task-123'}
        mock_clients['iam'].get_service_linked_role_deletion_status.return_value = {'Status': 'IN_PROGRESS'}
        delete_event = self._create_delete_event(SERVICE_LINKED_ROLE_NAME)
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "False"
        assert "timed out" in resp["Reason"]

    def test__delete_unknown_physical_resource_id(self, mocker):
        """Test deletion always attempts deletion regardless of PhysicalResourceId"""
        mocker.patch('time.sleep')
        mock_clients = self._setup_aws_mocks(mocker)
        mock_clients['iam'].delete_service_linked_role.return_value = {'DeletionTaskId': 'task-123'}
        mock_clients['iam'].get_service_linked_role_deletion_status.return_value = {'Status': 'SUCCEEDED'}
        delete_event = self._create_delete_event("unknown-format-id")
        
        resp = create_service_linked_role(delete_event)
        
        assert resp["Deleted"] == "True"

@pytest.mark.TDD
class TestClassTriggerSM:
    """TDD test class to handle state machine execution"""

    def test__success__fail(self, mocker):
        """success and exceptions for state machine execution"""

        # success
        mocker.patch(
            "solution.custom_resource.lib.step_functions.StepFunctions.trigger_state_machine"
        )
        context = LambdaContext()
        context._invoked_function_arn = "abc:abc:abc:abc:abc:abc:abc"
        start_state_machine({}, context)

        # failed
        mocker.patch(
            "solution.custom_resource.lib.step_functions.StepFunctions.trigger_state_machine",
            side_effect=ValueError("error triggering state machine"),
        )
        with pytest.raises(Exception):
            start_state_machine({}, context)

    def test_get_resource_type_details_add_vpc_tag(self):
        event = {
            "detail": {
                "changed-tag-keys": [
                    "Propagate-to",
                    "Associate-with"
                ],
                "resource-type": "vpc",
                "tags": {
                    "Propagate-to": "Flat",
                    "Associate-with": "Flat",
                    "Name": "test3"
                }
            },
            "account": "111111111111",
        }
        response = get_resource_type_details(event)
        assert response == "111111111111-added-vpc-tag"

    def test_get_resource_type_details_remove_subnet_tag(self):
        event = {
            "detail": {
                "changed-tag-keys": [
                    "Route-to-tgw"
                ],
                "service": "ec2",
                "resource-type": "subnet",
                "tags": {
                    "STNOStatus-Subnet": "2023-04-27T19:19:43Z",
                    "Name": "test2-subnet-private2-us-east-2a"
                }
            },
            "account": "111111111111",
        }
        response = get_resource_type_details(event)
        assert response == "111111111111-deleted-subnet-tag"

    def test_get_resource_type_details_add_subnet_tag(self):
        event = {
            "detail": {
                "changed-tag-keys": [
                    "Attach-to-tgw"
                ],
                "service": "ec2",
                "resource-type": "subnet",
                "tags": {
                    "Attach-to-tgw": "main-route-table-only",
                    "Name": "test2-subnet-private2-us-east-2a"
                }
            },
            "account": "111111111111",
        }
        response = get_resource_type_details(event)
        assert response == "111111111111-added-subnet-tag"


@pytest.mark.TDD
class TestClassSendCfnResponse:
    """TDD test class for send cfn response function"""

    def test__success__fail(self, mocker):
        """success and exceptions for state machine execution"""

        # success
        m1 = mocker.patch(
            "urllib.request.urlopen",
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


@pytest.mark.TDD
class TestClassAdditionalCoverage:
    def test_timeout_function(self, mocker):

        from solution.custom_resource.lib.custom_resource_helper import timeout
        mock_send = mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")
        
        timeout(CFN_REQUEST_EVENT, context)
        mock_send.assert_called_once_with(CFN_REQUEST_EVENT, context, "FAILED", {}, "Execution timed out")

    def test_handle_uuid_non_create(self):
        """Test handle_uuid for non-Create requests"""
        from solution.custom_resource.lib.custom_resource_helper import handle_uuid
        
        # Test Update request
        update_event = {"RequestType": "Update"}
        result = handle_uuid(update_event)
        assert result == {}
        
        # Test Delete request
        delete_event = {"RequestType": "Delete"}
        result = handle_uuid(delete_event)
        assert result == {}

    def test_handle_uuid_create_request(self):
        from solution.custom_resource.lib.custom_resource_helper import handle_uuid
        create_event = {"RequestType": "Create"}
        result = handle_uuid(create_event)
        assert "UUID" in result
        assert len(result["UUID"]) > 0

    def test_handle_cwe_permissions_delete(self, mocker):

        delete_event = deepcopy(CREATE_CWE_PERMISSIONS)
        delete_event["RequestType"] = "Delete"
        
        result = handle_cwe_permissions(delete_event)
        assert result is None

    def test_handle_prefix_delete(self):
    
        delete_event = deepcopy(CREATE_PREFIX)
        delete_event["RequestType"] = "Delete"
        
        result = handle_prefix(delete_event)
        assert result == {}


    def test_send_http_errors(self, mocker):

        from urllib.error import HTTPError, URLError
        
        # Test HTTPError
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = HTTPError(None, 500, "Server Error", None, None)
        
        with pytest.raises(HTTPError):
            send(CFN_REQUEST_EVENT, context, "SUCCESS", {})
        
        # Test URLError with reason attribute
        url_error = URLError("Connection failed")
        url_error.reason = "Network unreachable"
        mock_urlopen.side_effect = url_error
        
        with pytest.raises(URLError):
            send(CFN_REQUEST_EVENT, context, "SUCCESS", {})

    def test_send_with_long_reason_truncation(self, mocker):
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        

        long_reason = "x" * 300
        
        send(CFN_REQUEST_EVENT, context, "FAILED", {}, reason=long_reason)
        
        mock_urlopen.assert_called_once()

    def test_send_with_existing_physical_resource_id(self, mocker):
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        
        event_with_physical_id = deepcopy(CFN_REQUEST_EVENT)
        event_with_physical_id["PhysicalResourceId"] = "existing-physical-id"
        
        send(event_with_physical_id, context, "SUCCESS", {})
        
        mock_urlopen.assert_called_once()


    def test_timeout_handling_variations(self, mocker):
        from solution.custom_resource.lib.custom_resource_helper import timeout
        
        # Test with minimal context
        minimal_context = Mock()
        minimal_context.log_stream_name = "test-stream"
        mock_send = mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")
        
        timeout(CFN_REQUEST_EVENT, minimal_context)
        mock_send.assert_called_with(
            CFN_REQUEST_EVENT, 
            minimal_context, 
            "FAILED", 
            {}, 
            "Execution timed out"
        )

    def test_send_with_various_response_data(self, mocker):

        from solution.custom_resource.lib.custom_resource_helper import send
        
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        
        test_cases = [
            {},
            {"complex": {"nested": "data"}}, 
            {"list": [1, 2, 3]}, 
            {"none_value": None} 
        ]
        
        for response_data in test_cases:
            send(CFN_REQUEST_EVENT, context, "SUCCESS", response_data)
            assert mock_urlopen.called
            mock_urlopen.reset_mock()


    def test_send_with_none_reason(self, mocker):
        from solution.custom_resource.lib.custom_resource_helper import send
        
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        

        send(CFN_REQUEST_EVENT, context, "SUCCESS", {}, reason=None)
        mock_urlopen.assert_called_once()

    def test_start_state_machine_specific_branches(self, mocker):
        mocker.patch("solution.custom_resource.lib.step_functions.StepFunctions.trigger_state_machine")
        mock_get_resource_type = mocker.patch("solution.custom_resource.lib.custom_resource_helper.get_resource_type_details")
        mock_get_resource_type.return_value = "test-resource-type"
        
        context_mock = Mock()
        context_mock.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"

        event1 = {
            "account": "123456789",
            "detail": {
                "eventName": "DeleteSubnet"
            }
        }
        start_state_machine(event1, context_mock)

        event2 = {
            "account": "123456789", 
            "detail": {
                "resource-type": "vpc"
            }
        }
        start_state_machine(event2, context_mock)
        mock_get_resource_type.assert_called_once_with(event2)

    def test_cfn_handler_specific_resource_types(self, mocker):
        mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")

        mock_handle_prefix = mocker.patch("solution.custom_resource.lib.custom_resource_helper.handle_prefix")
        mock_handle_prefix.return_value = {"PrefixListArns": ["arn:test"]}
        
        prefix_event = deepcopy(CFN_REQUEST_EVENT)
        prefix_event["ResourceType"] = "Custom::GetPrefixListArns"
        cfn_handler(prefix_event, context)
        mock_handle_prefix.assert_called_once_with(prefix_event)

        mock_create_role = mocker.patch("solution.custom_resource.lib.custom_resource_helper.create_service_linked_role")
        mock_create_role.return_value = {"RoleName": SERVICE_LINKED_ROLE_NAME}
        
        role_event = deepcopy(CFN_REQUEST_EVENT)
        role_event["ResourceType"] = "Custom::CreateServiceLinkedRole"
        cfn_handler(role_event, context)
        mock_create_role.assert_called_once_with(role_event)

    def test_cfn_handler_console_deploy(self, mocker):
        mocker.patch("solution.custom_resource.lib.custom_resource_helper.send")
        mock_console_deploy = mocker.patch(
            "solution.custom_resource.lib.console_deployment.ConsoleDeployment.deploy"
        )
        mock_s3_client = mocker.patch("boto3.client")
        
        console_event = deepcopy(CFN_REQUEST_EVENT)
        console_event["ResourceType"] = "Custom::ConsoleDeploy"
        cfn_handler(console_event, context)
        

        mock_console_deploy.assert_called_once_with(console_event)
