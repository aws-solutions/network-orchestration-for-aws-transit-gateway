# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""SNS module"""

import logging
import boto3
from state_machine.lib.boto3_config import boto3_config


class SNS:
    """Class to handle SNS methods"""

    def __init__(self):
        """Initialize the SNS object's attributes"""
        self.logger = logging.getLogger(__name__)
        self.sns_client = boto3.client("sns", config=boto3_config)

    def publish(self, topic_arn, message, subject):
        """
        This method publishes a message to a given topic arn
        :param topic_arn: ARN for the SNS topic
        :param message: Message to be published
        :param subject: Subject of the message to be published
        """
        try:
            response = self.sns_client.publish(
                TopicArn=topic_arn, Message=message, Subject=subject
            )
            return response
        except Exception as error:
            self.logger.exception(
                f"Error while publishing sns message to the topic arn {topic_arn}"
            )
            self.logger.exception(error)
            raise
