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


class CloudWatchEvents(object):
    def __init__(self, logger):
        self.logger = logger
        self.cwe_client = boto3.client('events')

    def put_permission(self, principal, statement_id, event_bus_name, condition=None):
        """
        :action: required - This must be events:PutEvents (as of May 10th, 2019)
        :principal: required - Either account id or use '*' with condition where key is aws:PrincipalOrgID
        :statement_id: required - needed for remove_permission API
        :event_bus_name: required - custom event bus arn
        :condition: conditional - if added the type, key and value under condition are required
        :return: None
        """
        try:
            # if condition is present update the permission object
            if condition is not None:
                response = self.cwe_client.put_permission(
                    Action='events:PutEvents',
                    Principal=principal,
                    StatementId=statement_id,
                    Condition=condition,
                    EventBusName=event_bus_name
                )
            else:
                response = self.cwe_client.put_permission(
                    Action='events:PutEvents',
                    Principal=principal,
                    StatementId=statement_id,
                    EventBusName=event_bus_name
                )
            return response  # the API response if always return None
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def remove_permission(self, statement_id, event_bus_name):
        """
        :param statement_id: required - needed for remove_permission API
        :event_bus_name: required - custom event bus arn
        :return: None
        """
        try:
            response = self.cwe_client.remove_permission(
                StatementId=statement_id,
                EventBusName=event_bus_name
            )
            return response  # the API response if always return None
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.logger.info("Caught exception 'ResourceNotFoundException', the statement was already deleted")
                pass
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    @try_except_retry()
    def describe_event_bus(self, event_bus_name):
        """
        :param event_bus_name: required - custom event bus arn
        :return: {
            'Name': 'The name of the event bus. Currently, this is always default .',
            'Arn': 'The Amazon Resource Name (ARN) of the account permitted to write events to the current account.',
            'Policy': 'The policy that enables the external account to send events to your account.'
            }
        """
        try:
            response = self.cwe_client.describe_event_bus(
                Name=event_bus_name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
