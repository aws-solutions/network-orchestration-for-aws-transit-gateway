# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
from os import environ

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_logs
from mypy_boto3_logs import CloudWatchLogsClient

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.main import lambda_handler
from tgw_vpc_attachment.lib.clients.boto3_config import boto3_config


def test_process_failure():
    # ARRANGE
    override_environment_variables()

    # ACT
    response = lambda_handler({'params': {
        'ClassName': 'GeneralFunctions',
        'FunctionName': 'process_failure'
    }}, LambdaContext())

    # ASSERT
    assert response["Status"] == "failed"


@mock_logs
def test_log_failure_to_cloudwatch():
    # ARRANGE
    override_environment_variables()
    cw_logs, actions_log_group_name, failure_log_group_name = create_log_groups()

    event = {
        'Status': 'failed'
    }

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'GeneralFunctions',
            'FunctionName': 'log_in_cloudwatch',
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    failure_log_events = get_log_events(cw_logs, failure_log_group_name)
    assert len(failure_log_events) == 1
    assert json.loads(failure_log_events[0]['message']) == event


@mock_logs
def test_log_action_event_to_cloudwatch():
    # ARRANGE
    override_environment_variables()
    cw_logs, actions_log_group_name, failure_log_group_name = create_log_groups()

    event = {
        'Status': 'something'
    }

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'GeneralFunctions',
            'FunctionName': 'log_in_cloudwatch',
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    action_log_events = get_log_events(cw_logs, actions_log_group_name)
    assert len(action_log_events) == 1
    assert json.loads(action_log_events[0]['message']) == event


def create_log_groups():
    cw_logs: CloudWatchLogsClient = boto3.client("logs", config=boto3_config)
    failure_log_group_name = environ.get("LOG_GROUP_FAILURES")
    actions_log_group_name = environ.get("LOG_GROUP_ACTIONS")
    cw_logs.create_log_group(logGroupName=failure_log_group_name)
    cw_logs.create_log_group(logGroupName=actions_log_group_name)
    return cw_logs, actions_log_group_name, failure_log_group_name


def get_log_events(cw_logs, log_group_name):
    stream = cw_logs.describe_log_streams(
        logGroupName=log_group_name,
        orderBy='LastEventTime',
        descending=True,
        limit=1)['logStreams'][0]
    log_events = cw_logs.get_log_events(
        logGroupName=log_group_name,
        logStreamName=stream['logStreamName']
    )['events']
    return log_events
