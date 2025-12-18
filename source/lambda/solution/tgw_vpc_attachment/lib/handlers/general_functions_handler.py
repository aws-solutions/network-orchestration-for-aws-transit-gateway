# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import json
import os
from os import environ

from aws_lambda_powertools import Logger

from solution.tgw_vpc_attachment.lib.clients.cloud_watch_logs import CloudWatchLogs
from solution.tgw_vpc_attachment.lib.clients.sns import SNS
from solution.tgw_vpc_attachment.lib.utils.metrics import Metrics

EXECUTING = "Executing: "


class GeneralFunctions:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.logger.info(event)

    def send_failure_notification(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )

            error_message = self._build_error_message()
            self.event.update({"Comment": error_message, "Status": "failed"})
            self._send_to_sns_topic(error_message)

            return self.event

        except Exception as e:
            method = inspect.stack()[0][3]
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": method,
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            raise

    def _build_error_message(self):
        # We're expecting the event to contain an 'error-info' with the Exception details
        error_info = self.event.get("error-info", {})
        try:
            cause = json.loads(error_info["Cause"])
            error_message = cause["errorMessage"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning(f"Failed to parse error info: {str(e)}")
            error_message = str(error_info)
        return error_message

    def _send_to_sns_topic(self, error_message):
        # Send failure to SNS topic:
        try:
            notify = SNS()
            topic_arn = environ.get("FAILURE_NOTIFICATIONS_TOPIC")
            subject = "STNO: Failure event"
            message = (
                f"There has been a failed event in STNO. The error message is: {error_message}.\n\n"
                "The complete event JSON is: \n\n"
            )
            event_str = json.dumps(self.event, indent=4)
            message += event_str
            notify.publish(topic_arn, message, subject)
        except Exception as e:
            # The rest of the steps (failure logging) would not complete
            # if this step fails, so continue:
            self.logger.warning(f"Failed to send SNS notification: {str(e)}")

    def log_in_cloudwatch(self):
        """
        This method puts logs for the success and failure events.
        """
        log_group_actions = environ.get("LOG_GROUP_ACTIONS")
        log_group_failures = environ.get("LOG_GROUP_FAILURES")
        cw_log = CloudWatchLogs()
        event_message = json.dumps(self.event)
        if self.event.get("Status", "") == "failed":
            self.logger.debug(
                f"Adding the message {event_message} to the log group {log_group_failures}"
            )
            cw_log.log(log_group_failures, event_message)
        else:
            self.logger.debug(
                f"Adding the message {event_message} to the log group {log_group_actions}"
            )
            cw_log.log(log_group_actions, event_message)
        return self.event
