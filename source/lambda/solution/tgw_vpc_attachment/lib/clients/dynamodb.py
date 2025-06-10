# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import os

import boto3
from aws_lambda_powertools import Logger
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from mypy_boto3_dynamodb.type_defs import PutItemOutputTableTypeDef


class DDB:

    def __init__(self, table_name):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.table_name = table_name
        self.dynamodb_client: DynamoDBServiceResource = boto3.resource('dynamodb')
        self.table: Table = self.dynamodb_client.Table(self.table_name)

    def put_item(self, item) -> PutItemOutputTableTypeDef:
        try:
            response = self.table.put_item(Item=item)
            return response
        except Exception as error:
            self.logger.exception(f"Error while putting the item {item} in DynamoDB")
            self.logger.exception(error)
            raise error
