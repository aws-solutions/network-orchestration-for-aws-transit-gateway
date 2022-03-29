# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""DynamoDb module"""

import logging
import boto3


class DDB:
    """Class to handle CloudWatchLogs methods"""

    def __init__(self, table_name):
        """Initialize the DDB object's attributes"""
        self.logger = logging.getLogger(__name__)
        self.table_name = table_name
        self.dynamodb_client = boto3.resource('dynamodb')
        self.table = self.dynamodb_client.Table(self.table_name)

    def put_item(self, item):
        """
        This method puts the given item in DynamoDB
        :param item: Item to put in the DynamoDB table
        """
        try:
            response = self.table.put_item(
                Item=item
            )
            return response
        except Exception as error:
            self.logger.exception(f"Error while putting the item {item} in DynamoDB")
            self.logger.exception(error)
            raise
