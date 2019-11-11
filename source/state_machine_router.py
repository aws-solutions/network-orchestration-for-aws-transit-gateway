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

from state_machine_handler import TransitGateway, VPC, DynamoDb, ResourceAccessManager, ApprovalNotification
from lib.logger import Logger
import os
import inspect
import os.path
import sys

# initialise logger
LOG_LEVEL = os.environ['LOG_LEVEL']
logger = Logger(loglevel=LOG_LEVEL)

import botocore
import boto3

logger.info("boto3 version:" + boto3.__version__)
logger.info("botocore version:" + botocore.__version__)


def transit_gateway(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    tgw = TransitGateway(event, logger)
    if function_name == 'describe_transit_gateway_vpc_attachments':
        response = tgw.describe_transit_gateway_vpc_attachments()
    elif function_name == 'tgw_attachment_crud_operations':
        response = tgw.tgw_attachment_crud_operations()
    elif function_name == 'describe_transit_gateway_route_tables':
        response = tgw.describe_transit_gateway_route_tables()
    elif function_name == 'disassociate_transit_gateway_route_table':
        response = tgw.disassociate_transit_gateway_route_table()
    elif function_name == 'associate_transit_gateway_route_table':
        response = tgw.associate_transit_gateway_route_table()
    elif function_name == 'get_transit_gateway_attachment_propagations':
        response = tgw.get_transit_gateway_attachment_propagations()
    elif function_name == 'enable_transit_gateway_route_table_propagation':
        response = tgw.enable_transit_gateway_route_table_propagation()
    elif function_name == 'disable_transit_gateway_route_table_propagation':
        response = tgw.disable_transit_gateway_route_table_propagation()
    elif function_name == 'get_transit_gateway_vpc_attachment_state':
        response = tgw.get_transit_gateway_vpc_attachment_state()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}
    logger.info(response)
    return response


def vpc(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    vpc = VPC(event, logger)
    if function_name == 'describe_resources':
        response = vpc.describe_resources()
    elif function_name == 'default_route_crud_operations':
        response = vpc.default_route_crud_operations()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def ddb(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    ddb = DynamoDb(event, logger)
    if function_name == 'put_item':
        response = ddb.put_item()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def ram(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    ram = ResourceAccessManager(event, logger)
    if function_name == 'accept_resource_share_invitation':
        response = ram.accept_resource_share_invitation()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response

def sns(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    sns = ApprovalNotification(event, logger)
    if function_name == 'notify':
        response = sns.notify()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response

def lambda_handler(event, context):
    # Lambda handler function
    try:
        logger.debug("Lambda Handler Event")
        logger.debug(event)
        # Execute custom resource handlers
        class_name = event.get('params', {}).get('ClassName')
        function_name = event.get('params', {}).get('FunctionName')

        if class_name is not None:
            if class_name == "TransitGateway":
                return transit_gateway(event, function_name)
            elif class_name == 'VPC':
                return vpc(event, function_name)
            elif class_name == 'DynamoDb':
                return ddb(event, function_name)
            elif class_name == 'ResourceAccessManager':
                return ram(event, function_name)
            elif class_name == 'ApprovalNotification':
                return sns(event, function_name)
            else:
                message = "Class name does not match any class in the handler file."
                logger.info(message)
                return {"Message": message}
        else:
            message = "Class name not found in input."
            logger.info(message)
            return {"Message": message}
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise
