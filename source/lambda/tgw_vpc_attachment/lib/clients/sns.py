# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_sns import SNSClient
from mypy_boto3_sns.type_defs import PublishResponseTypeDef

from tgw_vpc_attachment.lib.clients.boto3_config import boto3_config


class SNS:

    def __init__(self):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.sns_client: SNSClient = boto3.client("sns", config=boto3_config)

    def publish(self, topic_arn: str, message: str, subject: str) -> PublishResponseTypeDef:
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
            raise error
