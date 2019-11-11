######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# !/bin/python

import boto3
import inspect
from lib.decorator import try_except_retry
from botocore.exceptions import ClientError
from json import dumps, JSONEncoder
from decimal import Decimal

dynamodb_client = boto3.resource('dynamodb')

class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


class DDB(object):
    def __init__(self, logger, table_name):
        self.logger = logger
        self.table_name = table_name
        self.table = dynamodb_client.Table(self.table_name)

    @try_except_retry()
    # DDB API call to get an item
    def get_item(self, key, value):
        try:
            response = self.table.get_item(
                Key={
                    key: value
                }
            )
            item = response.get('Item')
            self.logger.info('Printing DynamoDB Item')
            self.logger.info(dumps(item, indent=4, cls=DecimalEncoder))
            return item
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    # DDB API call to put an item
    def put_item(self, item):
        try:
            response = self.table.put_item(
                Item=item
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
