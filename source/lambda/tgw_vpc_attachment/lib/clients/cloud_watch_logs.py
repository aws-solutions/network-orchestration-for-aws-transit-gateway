# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import uuid
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger

from tgw_vpc_attachment.lib.clients.boto3_config import boto3_config


class CloudWatchLogs:

    def __init__(self):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.cw_logs = boto3.client("logs", config=boto3_config)

    def log(self, log_group, message):
        """
        This method creates a log stream and puts log message
        :param log_group: Name of the log group
        :param message: Event or message to put in th elog group
        """
        self.logger.debug(
            f"Calling the log method with log group {log_group} and message {message}"
        )
        uuid_str = str(uuid.uuid4())
        timestamp_str = datetime.utcnow().strftime("%Y/%m/%d/%H/%M/%S")
        log_stream = f"{timestamp_str}-{uuid_str}"
        self.create_log_stream(log_group, log_stream)
        self.put_log_events(log_stream, log_group, message)

    def create_log_stream(self, log_group, log_stream):
        """
        This method creates a log stream
        :param log_group: Name of the log group
        :param log_stream: Name of the log stream
        """
        self.logger.debug(
            f"Creating log stream with name {log_stream} for the log group {log_group}"
        )
        try:
            self.cw_logs.create_log_stream(
                logGroupName=log_group,
                logStreamName=log_stream,
            )
        except Exception as error:
            self.logger.warning(
                f"Failed to create log stream {log_stream} for the log group {log_group}"
            )
            self.logger.warning(error)

    def put_log_events(self, log_stream, log_group, message):
        """
        This method puts log messages in log stream
        :param log_group: Name of the log group
        :param log_stream: Name of the log stream
        :param message: Event or message to put in th elog group
        """
        self.logger.debug(
            f"Putting the message {message} in the log stream {log_stream} with log group {log_group}"
        )
        try:
            self.cw_logs.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "message": message,
                    }
                ],
            )
        except Exception as error:
            self.logger.warning(
                f"Failed to add message {message} in the log stream {log_stream} with log group {log_group}"
            )
            self.logger.warning(error)
