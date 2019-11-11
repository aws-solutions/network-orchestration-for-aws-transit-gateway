######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# !/bin/python

from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.cloud_watch_events import CloudWatchEvents
from lib.metrics import Metrics
from os import environ
import time
import inspect
from lib.helper import sanitize, get_region
from lib.s3 import S3
import os
import json
from uuid import uuid4


class StepFunctions(object):
    # Execute State Machines
    def __init__(self, event, logger):
        self.logger = logger
        self.event = event
        self.logger.info("State Machine Event")
        self.logger.info(event)

    def trigger_state_machine(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            sm = StateMachine(self.logger)
            account_id = self.event.get('account')
            resource_type = 'stno-console' if self.event.get('detail', {}).get('resource-type') is None \
                else account_id + '-' + self.event.get('detail', {}).get('resource-type') + '-tagged'
            state_machine_arn = environ.get('STATE_MACHINE_ARN')

            # Execute State Machine

            exec_name = "%s-%s-%s" % ('event-from', resource_type, time.strftime("%Y-%m-%dT%H-%M-%S-%s"))
            self.event.update({'StateMachineArn': state_machine_arn})

            self.logger.info("Triggering {} State Machine".format(state_machine_arn.split(":", 6)[6]))
            response = sm.trigger_state_machine(state_machine_arn, self.event, sanitize(exec_name))
            self.logger.info("State machine triggered successfully, Execution Arn: {}".format(response))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


class SecureSSMParameters(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Put Secure SSM Parameter Values Handler Event")

    ''' This function creates or updates key value pair in SSM parameter store as a secure string.
        The value will be encrypted with the AWS managed key 'aws/ssm' '''
    def create_secure_ssm_parameter(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ssm = SSM(self.logger)
            # put values from SSM Parameter Store as a secure string
            # if the key already exists the value will be overwritten
            self.logger.info("Create/Update Secure SSM Parameter Key: {}".format(self.params.get('PSKey')))
            response = ssm.put_parameter(self.params.get('PSKey'),
                                         self.params.get('PSValue'),
                                         self.params.get('PSDescription'),
                                         'SecureString')
            self.logger.info(response)
            return response  # return version number
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    ''' This delete the key value pair in SSM parameter store.'''
    def delete_secure_ssm_parameter(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ssm = SSM(self.logger)
            self.logger.info("Delete Secure SSM Parameter Key: {}".format(self.params.get('PSKey')))
            response = ssm.delete_parameter(self.params.get('PSKey'))
            return response  # should be empty dict {}
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


class CWEventPermissions(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.event_bus_name = self.params.get('EventBusName')
        self.logger = logger
        self.logger.info("CloudWatch Event Permissions Handler Event")
        self.logger.info(event)

    def _print_policy(self, cwe):
        self.logger.info("Describe Event Bus")
        response = cwe.describe_event_bus(self.event_bus_name)
        policy = 'Policy Not Found' if response.get('Policy') is None else json.loads(response.get('Policy'))
        self.logger.info("Printing Policy")
        self.logger.info(policy)

    def _is_valid_account_length(self, principal):
        account_id_length = 12
        if len(principal) == account_id_length:
            self.logger.info('The AWS Account ID is 12-digit number. Continuing... ')
        else:
            raise Exception('The AWS Account ID should be 12-digit number.')

    def _create(self, principal_list):
        cwe = CloudWatchEvents(self.logger)
        # identify if principal is list of account IDs or organization arn
        response = None
        self.logger.info("Adding following principals to the policy: {}".format(principal_list))
        for principal in principal_list:
            if 'arn:aws:organizations' in principal:
                self.logger.info('Adding Organization ID to the policy: {}'.format(principal))
                split_value = principal.split('/')[-1]
                condition = {
                    'Type': 'StringEquals',
                    'Key': 'aws:PrincipalOrgID',
                    'Value': split_value
                }
                # Once we specify a condition with an AWS organization ID, the recommendation is we use "*" as the value
                # for Principal to grant permission to all the accounts in the named organization.
                response = cwe.put_permission('*', split_value, self.event_bus_name, condition)
            else:
                self._is_valid_account_length(principal)
                self.logger.info('Adding spoke account ID to the policy: {}'.format(principal))
                response = cwe.put_permission(principal, principal, self.event_bus_name)
            self._print_policy(cwe)
        return response

    def create_permissions(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # put permissions
            # analyze if the principals is a list of accounts or Org Arn
            self._create(self.params.get('Principals'))
            return None
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_permissions(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # update permissions
            response = None
            principal_list = self.params.get('Principals')
            old_params = self.event.get('OldResourceProperties')
            old_principal_list = old_params.get('Principals')
            # Generate add and remove lists for update process
            delete_list = list(set(old_principal_list) - set(principal_list))
            self.logger.info('Remove permission for following principal(s): {}'.format(delete_list))

            # if list is not empty
            if delete_list:
                response = self._delete(delete_list)

            add_list = list(set(principal_list) - set(old_principal_list))
            self.logger.info('Put permission for following principal(s): {}'.format(add_list))

            # if list is not empty
            if add_list:
                response = self._create(add_list)

            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def _delete(self, principal_list):
        cwe = CloudWatchEvents(self.logger)
        self.logger.info("Removing following principals from the policy: {}".format(principal_list))
        # identify if principal is list of account IDs or organization arn
        response = None
        for principal in principal_list:
            if 'arn:aws:organizations' in principal:
                self.logger.info('Deleting Organization ID from the policy: {}'.format(principal))
                split_value = principal.split('/')[-1]
                response = cwe.remove_permission(split_value, self.event_bus_name)
            else:
                self.logger.info('Deleting spoke account ID from the policy: {}'.format(principal))
                response = cwe.remove_permission(principal, self.event_bus_name)
            self._print_policy(cwe)
        return response

    def delete_permissions(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # delete permissions
            # analyze if the principals is a list of accounts or Org Arn
            response = self._delete(self.params.get('Principals'))
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


# Deploy all the files needed for console to customer's S3 bucket and
# update the configuration file with customer configurations
class S3ConsoleDeploy(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Upload console content to s3")
        self.logger.info(event)
        
    # Upload console content listed in the manifest file to customer's s3 bucket    
    def upload_console_files(self):
        try:
            s3 = S3(self.logger)
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])

            file_path = os.path.join(os.path.dirname(__file__), "console-manifest.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as json_data:
                    data = json.load(json_data)
                    
                destination_bucket = self.params.get('ConsoleBucket')
                source_bucket = self.params.get('SrcBucket')
                key_prefix = self.params.get('SrcPath') + '/'

                for file in data["files"]:
                    key = 'console/' + file
                    s3.copy_object(source_bucket, key_prefix, key, destination_bucket)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    # Upload the configuration file having customer configurations to customer's s3 bucket
    def upload_config_file(self):
        try:
            s3 = S3(self.logger)
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])

            stno_config = {
                "aws_project_region": self.params.get("AwsProjectRegion"),
                "aws_cognito_region": self.params.get("AwsCognitoRegion"),
                "aws_user_pools_id": self.params.get("AwsUserPoolsId"),
                "aws_user_pools_web_client_id": self.params.get("AwsUserPoolsWebClientId"),
                "aws_cognito_identity_pool_id": self.params.get("AwsCognitoIdentityPoolId"),
                "oauth": {},
                "aws_appsync_graphqlEndpoint": self.params.get("AwsAppsyncGraphqlEndpoint"),
                "aws_appsync_region": self.params.get("AwsAppsyncRegion"),
                "aws_appsync_authenticationType": "AMAZON_COGNITO_USER_POOLS",
                "aws_content_delivery_bucket": self.params.get("AwsContentDeliveryBucket"),
                "aws_content_delivery_bucket_region": self.params.get("AwsContentDeliveryBucketRegion"),
                "aws_content_delivery_url": self.params.get("AwsContentDeliveryUrl")
            }

            configurations = 'const stno_config = ' + json.dumps(stno_config) + ';'
            console_bucket = self.params.get('ConsoleBucket')
            key = 'console/assets/stno_config.js'

            s3.put_object(console_bucket, key, configurations)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


# Send anonymous metrics
class CFNMetrics(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(event)

    def put_ssm_parameter(self, key, value):
        try:
            ssm = SSM(self.logger)
            response = ssm.describe_parameters(key)
            self.logger.info(response)
            # put parameter if key does not exist
            if not response:
                ssm.put_parameter(key, value)
        except Exception as e:
            self.logger.info(e)
            pass

    # put metrics_flag and uuid in the parameter store
    def put_ssm(self):
        try:
            # create SSM parameters to send anonymous data if opted in
            flag_value = self.params.get('MetricsFlag')
            self.put_ssm_parameter('/solutions/stno/metrics_flag', flag_value)
            self.put_ssm_parameter('/solutions/stno/customer_uuid', str(uuid4()))
        except Exception as e:
            self.logger.info(e)
            pass

    # Upload the configuration file having customer configurations to customer's s3 bucket
    def send_metrics(self):
        try:
            self.put_ssm()
            self.logger.info(self.params)
            data = {
                "PrincipalType": self.params.get('PrincipalType'),
                "ApprovalNotificationFlag": self.params.get('ApprovalNotification'),
                "AuditTrailRetentionPeriod": self.params.get('AuditTrailRetentionPeriod'),
                "DefaultRoute": self.params.get('DefaultRoute'),
                "Region": get_region(),
                "SolutionVersion": self.params.get('SolutionVersion')
            }
            send = Metrics(self.logger)
            send.metrics(data)
        except Exception as e:
            self.logger.info(e)
            pass
