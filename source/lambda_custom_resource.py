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

from hashlib import md5
from lib.crhelper import cfn_handler
from custom_resource_handler import StepFunctions, SecureSSMParameters, CWEventPermissions, S3ConsoleDeploy, CFNMetrics
from lib.logger import Logger
import os
import inspect


# initialise logger
LOG_LEVEL = os.environ.get('LOG_LEVEL')
if LOG_LEVEL is None:
    LOG_LEVEL = 'info'
logger = Logger(loglevel=LOG_LEVEL)
init_failed = False


def create(event, context):
    """
    Runs on Stack Creation.
    As there is no real 'resource', and it will never be replaced,
    PhysicalResourceId is set to a hash of StackId and LogicalId.
    """
    s = '%s-%s' % (event.get('StackId'), event.get('LogicalResourceId'))
    physical_resource_id = md5(s.encode('UTF-8')).hexdigest()

    if event.get('ResourceType') == 'Custom::SecureSSMStrings':
        ssm = SecureSSMParameters(event, logger)
        logger.info("Create Secure Parameter (SSM) - CR Router")
        response = ssm.create_secure_ssm_parameter()
        logger.info("Response from Create Secure SSM Parameter CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::CWEventPermissions':
        cwe = CWEventPermissions(event, logger)
        logger.info("Create CW Event Bus Policy - CR Router")
        response = cwe.create_permissions()
        logger.info("Response from Create Policy CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::ConsoleDeploy':
        cd = S3ConsoleDeploy(event, logger)
        logger.info("Deploy console content to s3")
        cd.upload_console_files()
        cd.upload_config_file()
        response = None
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::SendCFNParameters':
        send = CFNMetrics(event, logger)
        send.send_metrics()
        response = None
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def update(event, context):
    """
    Runs on Stack Update
    """
    physical_resource_id = event['PhysicalResourceId']
    if event.get('ResourceType') == 'Custom::SecureSSMStrings':
        ssm = SecureSSMParameters(event, logger)
        logger.info("Update Secure Parameter (SSM)- CR Router")
        response = ssm.create_secure_ssm_parameter()
        logger.info("Response from Update Secure SSM Parameter CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::CWEventPermissions':
        cwe = CWEventPermissions(event, logger)
        logger.info("Updating CW Event Bus Policy - CR Router")
        response = cwe.update_permissions()
        logger.info("Response from Update Policy CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::ConsoleDeploy':
        cd = S3ConsoleDeploy(event, logger)
        logger.info("Update and deploy customer console config file to s3")
        cd.upload_console_files()
        cd.upload_config_file()
        response = None
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::SendCFNParameters':
        send = CFNMetrics(event, logger)
        send.send_metrics()
        response = None
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def delete(event, context):
    """
    Runs on Stack Delete.
    """
    if event.get('ResourceType') == 'Custom::SecureSSMStrings':
        ssm = SecureSSMParameters(event, logger)
        logger.info("Delete Secure Parameter (SSM) - CR Router")
        response = ssm.delete_secure_ssm_parameter()
        logger.info("Response from Delete Secure SSM Parameter CR Handler")
        logger.info(response)
        return response
    elif event.get('ResourceType') == 'Custom::CWEventPermissions':
        cwe = CWEventPermissions(event, logger)
        logger.info("Deleting CW Event Bus Policy - CR Router")
        response = cwe.delete_permissions()
        logger.info("Response from Delete Policy CR Handler")
        logger.info(response)
        return response
    elif event.get('ResourceType') == 'Custom::ConsoleDeploy':
        logger.info("No action required, returning 'None'")
        response = None
        return response
    elif event.get('ResourceType') == 'Custom::SendCFNParameters':
        logger.info("No action required, returning 'None'")
        response = None
        return response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def lambda_handler(event, context):
    # Lambda handler function uses cr helper library to handle CloudFormation services
    try:
        logger.info("<<<<<<<<<< Custom Resource lambda_handler Event >>>>>>>>>>")
        # if the event is from the CloudWatch Events Service then invoke the state machine
        if event.get('source') == 'aws.tag' and event.get('detail-type') == 'Tag Change on Resource':
            logger.info('Event received from CloudWatch Event Service')
            logger.info(event)
            state_machine = StepFunctions(event, logger)
            state_machine.trigger_state_machine()
        # else if the event is from Cloudformation Service
        elif event.get('StackId') is not None and 'arn:aws:cloudformation' in event.get('StackId'):
            logger.info('Event received from Cloudformation Service')
            if event.get('ResourceType') != 'Custom::SecureSSMStrings':
                logger.info(event)  # avoid printing sensitive data in the logs
            return cfn_handler(event, context, create, update, delete, logger, init_failed)
        # else of the event is from Web Application
        elif event.get('data') is not None:
            logger.info('Event received from Web App - Transit Network Management Console')
            logger.info(event)
            state_machine = StepFunctions(event.get('data'), logger)
            state_machine.trigger_state_machine()
        else:
            logger.info(event)
            logger.error('The event is from an invalid source')
            raise Exception('The event is neither from CloudWatch Event service or from Cloudformation service.')
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise
