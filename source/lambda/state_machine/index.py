# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Router module"""

import os.path

import boto3
import botocore
from aws_lambda_powertools import Logger

from state_machine.lib.exceptions import (
    ResourceNotFoundException,
    AttachmentCreationInProgressException,
    AlreadyConfiguredException,
    ResourceBusyException,
)
from state_machine.lib.handlers.approval_notifications_handler import ApprovalNotification
from state_machine.lib.handlers.dynamodb_handler import DynamoDb
from state_machine.lib.handlers.general_functions_handler import GeneralFunctions
from state_machine.lib.handlers.resource_access_manager_handler import ResourceAccessManager
from state_machine.lib.handlers.transit_gateway_handler import TransitGateway
from state_machine.lib.handlers.vpc_handler import VPC

logger = Logger(os.getenv('LOG_LEVEL'))
ERROR_MESSAGE = "Function name does not match any function in the handler file."
ROUTER_FUNCTION_NAME = "Router Function Name: {}"

logger.debug("boto3 version:" + boto3.__version__)
logger.debug("botocore version:" + botocore.__version__)


def lambda_handler(event, _):
    try:
        logger.info("Lambda Handler Event")
        logger.info(event)
        class_name = event.get("params", {}).get("ClassName")
        function_name = event.get("params", {}).get("FunctionName")
        event = event.get("event", {})

        if class_name is not None:
            if class_name == "TransitGateway":
                return transit_gateway(event, function_name)
            elif class_name == "VPC":
                return vpc(event, function_name)
            elif class_name == "DynamoDb":
                return dynamo_db(event, function_name)
            elif class_name == "ResourceAccessManager":
                return resource_access_manager(event, function_name)
            elif class_name == "ApprovalNotification":
                return sns(event, function_name)
            elif class_name == "GeneralFunctions":
                return general_functions(event, function_name)
            else:
                logger.info(ERROR_MESSAGE)
                return {"Message": ERROR_MESSAGE}
        else:
            message = "Class name not found in input."
            logger.info(message)
            return {"Message": message}
    except (
            ResourceNotFoundException,
            AttachmentCreationInProgressException,
            AlreadyConfiguredException,
            ResourceBusyException,
    ) as e:
        raise e
    except Exception as error:
        logger.exception("Error while executing lambda handler")
        logger.exception(error)
        raise


def transit_gateway(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    tgw = TransitGateway(event)
    if function_name == "describe_transit_gateway_vpc_attachments":
        response = tgw.describe_transit_gateway_vpc_attachments()
    elif function_name == "tgw_attachment_crud_operations":
        response = tgw.tgw_attachment_crud_operations()
    elif function_name == "describe_transit_gateway_route_tables":
        response = tgw.describe_transit_gateway_route_tables()
    elif function_name == "disassociate_transit_gateway_route_table":
        response = tgw.disassociate_transit_gateway_route_table()
    elif function_name == "associate_transit_gateway_route_table":
        response = tgw.associate_transit_gateway_route_table()
    elif function_name == "get_transit_gateway_attachment_propagations":
        response = tgw.get_transit_gateway_attachment_propagations()
    elif function_name == "enable_transit_gateway_route_table_propagation":
        response = tgw.enable_transit_gateway_route_table_propagation()
    elif function_name == "disable_transit_gateway_route_table_propagation":
        response = tgw.disable_transit_gateway_route_table_propagation()
    elif function_name == "get_transit_gateway_vpc_attachment_state":
        response = tgw.get_transit_gateway_vpc_attachment_state()
    elif function_name == "tag_transit_gateway_attachment":
        response = tgw.tag_transit_gateway_attachment()
    elif function_name == "subnet_deletion_event":
        response = tgw.subnet_deletion_event()
    elif function_name == "update_tags_if_failed":
        response = tgw.update_tags_if_failed()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}
    logger.info(response)
    return response


def vpc(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    vpc = VPC(event)
    if function_name == "describe_resources":
        response = vpc.describe_resources()
    elif function_name == "default_route_crud_operations":
        response = vpc.default_route_crud_operations()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}

    logger.info(response)
    return response


def dynamo_db(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    ddb = DynamoDb(event)
    if function_name == "put_item":
        response = ddb.put_item()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}

    logger.info(response)
    return response


def resource_access_manager(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    ram = ResourceAccessManager(event)
    if function_name == "accept_resource_share_invitation":
        response = ram.accept_resource_share_invitation()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}

    logger.info(response)
    return response


def sns(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    sns = ApprovalNotification(event)
    if function_name == "notify":
        response = sns.notify()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}

    logger.info(response)
    return response


def general_functions(event, function_name):
    logger.info(ROUTER_FUNCTION_NAME.format(function_name))

    general = GeneralFunctions(event)
    if function_name == "process_failure":
        response = general.send_failure_notification()
    elif function_name == "log_in_cloudwatch":
        response = general.log_in_cloudwatch()
    else:
        logger.info(ERROR_MESSAGE)
        return {"Message": ERROR_MESSAGE}
    logger.info(response)
    return response
