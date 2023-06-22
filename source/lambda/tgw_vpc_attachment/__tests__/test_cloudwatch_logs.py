# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

os.environ["USER_AGENT_STRING"] = ""
from tgw_vpc_attachment.lib.clients.cloud_watch_logs import CloudWatchLogs
from botocore.stub import Stubber
from freezegun import freeze_time


@freeze_time("2022-01-22")
def test_put_log_events_success(mocker):
    cloudwatch_logs = CloudWatchLogs()
    client_stubber = Stubber(cloudwatch_logs.cw_logs)
    log_stream = "test_stream"
    log_group = "test_log_group"
    message = "Test Message"
    response = {}
    expected_params = {
        "logGroupName": log_group,
        "logStreamName": log_stream,
        "logEvents": [{"timestamp": 1642809600000, "message": message}],
    }

    spy_logger = mocker.spy(cloudwatch_logs.logger, "debug")
    client_stubber.add_response("put_log_events", response, expected_params)
    client_stubber.activate()
    cloudwatch_logs.put_log_events(log_stream, log_group, message)
    assert spy_logger.call_count == 1


@freeze_time("2022-01-22")
def test_put_log_events_exception(mocker):
    cloudwatch_logs = CloudWatchLogs()
    client_stubber = Stubber(cloudwatch_logs.cw_logs)
    log_stream = "test_stream"
    log_group = "test_log_group"
    message = "Test Message"
    spy_logger = mocker.spy(cloudwatch_logs.logger, "warning")
    client_stubber.add_client_error("put_log_events", "Invalid_request")
    client_stubber.activate()
    cloudwatch_logs.put_log_events(log_stream, log_group, message)
    assert spy_logger.call_count == 2


def test_create_log_stream_success(mocker):
    cloudwatch_logs = CloudWatchLogs()
    client_stubber = Stubber(cloudwatch_logs.cw_logs)
    log_stream = "test_stream"
    log_group = "test_log_group"
    response = {}
    expected_params = {"logGroupName": log_group, "logStreamName": log_stream}

    spy_logger = mocker.spy(cloudwatch_logs.logger, "debug")
    client_stubber.add_response("create_log_stream", response, expected_params)
    client_stubber.activate()
    cloudwatch_logs.create_log_stream(log_group, log_stream)
    assert spy_logger.call_count == 1


def test_create_log_stream_exception(mocker):
    cloudwatch_logs = CloudWatchLogs()
    client_stubber = Stubber(cloudwatch_logs.cw_logs)
    log_stream = "test_stream"
    log_group = "test_log_group"
    spy_logger = mocker.spy(cloudwatch_logs.logger, "warning")
    client_stubber.add_client_error("create_log_stream", "Invalid_request")
    client_stubber.activate()
    cloudwatch_logs.create_log_stream(log_group, log_stream)
    assert spy_logger.call_count == 2


def test_log(mocker):
    cloudwatch_logs = CloudWatchLogs()
    log_group = "test_log_group"
    message = "Test Message"
    mocker.patch.object(cloudwatch_logs, "put_log_events")
    mocker.patch.object(cloudwatch_logs, "create_log_stream")
    spy_put_log_events = mocker.spy(cloudwatch_logs, "put_log_events")
    spy_create_log_stream = mocker.spy(cloudwatch_logs, "create_log_stream")
    cloudwatch_logs.log(log_group, message)
    spy_put_log_events.assert_called_once()
    spy_create_log_stream.assert_called_once()
