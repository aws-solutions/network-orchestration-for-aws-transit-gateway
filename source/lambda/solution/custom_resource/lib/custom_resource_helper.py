# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource helper module"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from os import environ, path
from urllib import request, error
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_typing import events

from solution.custom_resource.lib.cloudwatch_events import CloudWatchEvents
from solution.custom_resource.lib.console_deployment import ConsoleDeployment
from solution.custom_resource.lib.step_functions import StepFunctions
from solution.custom_resource.lib.utils import boto3_config
from solution.custom_resource.lib.utils import (
    sanitize,
    send_metrics,
    METRICS_TIMESTAMP_FORMAT,
)

logger = Logger(os.getenv('LOG_LEVEL'))

def start_state_machine(event: events.CloudFormationCustomResourceEvent, context: LambdaContext):
    log_message = {
        "METHOD": "trigger_sm",
    }
    try:
        lambda_function_arn = context.invoked_function_arn
        hub_account_id = lambda_function_arn.split(":")[4]
        aws_partition = lambda_function_arn.split(":")[1]
        aws_region = environ.get('AWS_REGION')
        state_machine = StepFunctions()
        account_id = event.get("account")
        if event.get("detail", {}).get("eventName") == "DeleteSubnet":
            resource_type = account_id + "subnet-deletion"
        elif event.get("detail", {}).get("resource-type"):
            resource_type = get_resource_type_details(event)
        else:
            resource_type = "stno-console"

        state_machine_arn = f"arn:{aws_partition}:states:{aws_region}:{hub_account_id}:stateMachine:STNO-StateMachine"
        log_message["MESSAGE"] = f"triggering state machine {state_machine_arn}"
        logger.debug(str(log_message))
        exec_name = f"event-from-{resource_type}-{time.strftime('%Y-%m-%dT%H-%M-%S-%s')}"
        event.update({"StateMachineArn": state_machine_arn})
        state_machine.trigger_state_machine(
            state_machine_arn, event, sanitize(exec_name)
        )
    except Exception as err:
        log_message["EXCEPTION"] = str(err)
        logger.error(str(log_message))
        raise


def get_resource_type_details(event):
    event_name = (
            event.get("account")
            + get_tag_state(event)
            + event.get("detail", {}).get("resource-type")
            + "-tag"

    )
    # avoid reaching state machine execution name quota
    return event_name[:35] if len(event_name) > 35 else event_name


def get_tag_state(event):
    resource_details = event.get('detail')
    tags_in_event = set(resource_details.get('changed-tag-keys'))
    tags_on_resource = set(resource_details.get('tags').keys())
    common_tags = tags_in_event & tags_on_resource
    if common_tags:
        return "-added-"
    elif not common_tags:
        return "-deleted-"


def timeout(event: events.CloudFormationCustomResourceEvent, context: LambdaContext):
    """_summary_

    Args:
        event (_type_): _description_
        context (_type_): _description_
    """
    logger.error("Execution is about to time out, sending failure message")
    send(event, context, "FAILED", {}, "Execution timed out")


def cfn_handler(event: events.CloudFormationCustomResourceEvent, context: LambdaContext):
    """Handler for cfn triggered events

    Args:
        event (dict): event from CloudFormation on create, update or delete
        context (object): lambda context object to the handler

    Returns:
        None

    Reference: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref.html
    """

    log_message = {
        "METHOD": "cfn_handler",
    }
    # Define an object to place any response information you would like to send
    # back to CloudFormation (these keys can then be used by Fn::GetAttr)
    response_data = {}
    status = "SUCCESS"
    reason = None
    request_type = event.get('RequestType', '').lower()

    # Setup timer to catch timeouts
    timer = threading.Timer(
        (context.get_remaining_time_in_millis() / 1000.00) - 0.5,
        timeout,
        args=[event, context, logger],
    )
    timer.start()
    try:
        resource_type = event.get("ResourceType")
        log_message["MESSAGE"] = f"{event.get('RequestType')} for {resource_type}"
        logger.debug(str(log_message))
        
        if resource_type == "Custom::SendCFNParameters":
            handle_metrics(event)

        elif resource_type == "Custom::CreateUUID":
            response_data = handle_uuid(event)
        elif resource_type == "Custom::CWEventPermissions":
            handle_cwe_permissions(event)
        elif resource_type == "Custom::ConsoleDeploy":
            s3_client = boto3.client("s3", config=boto3_config)
            ConsoleDeployment(s3_client, open, path.exists).deploy(event)
        elif resource_type == "Custom::GetPrefixListArns":
            response_data = handle_prefix(event)
        elif resource_type == "Custom::CheckServiceLinkedRole":
            response_data = check_service_linked_role(event)

        logger.info("Completed successfully, sending response to cfn")
    except Exception as err:
        log_message["EXCEPTION"] = str(err)
        logger.error(str(log_message))
        status = "FAILED"
        reason = str(err)
    finally:        
        send(
            event,
            context,
            status,
            response_data,
            reason,
        )
        timer.cancel()


def handle_uuid(event: events.CloudFormationCustomResourceEvent):
    """Generates UUID for solution deployment

    Args:
       event (dict): event from CloudFormation on create, update or delete

    Returns:
        dict: UUID for the solution deployment

        {
            UUID: string
        }
    """
    resp = {}
    if event["RequestType"] == "Create":
        resp = {"UUID": str(uuid4())}
    return resp


def handle_cwe_permissions(event: events.CloudFormationCustomResourceEvent):
    """Handler for CloudWatch EventBridge permissions crud operations

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        None
    """
    cwe = CloudWatchEvents()
    request_type = event["RequestType"]
    properties = event["ResourceProperties"]
    event_bus_name = properties.get("EventBusName")

    principal_list = properties.get("Principals")
    if request_type == "Create":
        for principal in principal_list:
            cwe.put_permission(principal, event_bus_name)
    if request_type == "Delete":
        # No need to delete the policy as Event Bus deletion will automatically delete the policy
        # This also protects us from deletion of policy in the CFN cleanup process
        return None
    if request_type == "Update":
        old_properties = event.get("OldResourceProperties")
        old_principal_list = old_properties.get("Principals")
        delete_list = list(set(old_principal_list) - set(principal_list))
        for principal in delete_list:
            cwe.remove_permission(principal, event_bus_name)
        for principal in principal_list:
            cwe.put_permission(principal, event_bus_name)


def handle_prefix(event: events.CloudFormationCustomResourceEvent):
    """Handles generating prefix list arns from prefix list

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        dict: prefix list arns

        {
            PrefixListArns: string[]
        }
    """
    response = {}
    if event["RequestType"] == "Create" or event["RequestType"] == "Update":
        properties = event["ResourceProperties"]
        prefix_list = properties.get("PrefixListIds")
        account_id = properties.get("AccountId")
        list_of_prefix_list_ids = prefix_list.replace(' ', '').split(',')
        list_of_prefix_list_arns = []
        if not prefix_list:
            raise ValueError(
                "STNO CFN Parameter Missing: You must "
                "provide at least one valid prefix list id."
            )
        for prefix_list_id in list_of_prefix_list_ids:
            arn = f"arn:{environ.get('PARTITION')}:ec2:{environ.get('AWS_REGION')}:{account_id}:prefix-list/{prefix_list_id}"
            list_of_prefix_list_arns.append(arn)
        response = {"PrefixListArns": list_of_prefix_list_arns}
    return response


def handle_metrics(event: events.CloudFormationCustomResourceEvent):
    """Handles sending launch parameters to aws-solutions 

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        None
    """
    properties = event["ResourceProperties"]
    request_type = event.get('RequestType', '').lower()
    data = {
        "event": {
            "type": "solution",
            "action": request_type
        },
        "solution": {
            "PrincipalType": properties.get("PrincipalType"),
            "ApprovalNotificationFlag": properties.get("ApprovalNotification"),
            "AuditTrailRetentionPeriod": properties.get(
                "AuditTrailRetentionPeriod"
            ),
            "DefaultRoute": properties.get("DefaultRoute"),
            "DeployWebUI": properties.get("DeployWebUI"),
            "Region": environ.get("AWS_REGION"),
            "CreatedNewTransitGateway": properties.get(
                "CreatedNewTransitGateway"
            )
        },
        "version": environ.get("SOLUTION_VERSION")
    }
    cfn_client = boto3.client('cloudformation', config=boto3_config)
    creation_time = None
    created_at = None
    try:
        stack_info = cfn_client.describe_stacks(StackName=event['StackId'])
        if stack_info['Stacks']:
            creation_time = stack_info['Stacks'][0]['CreationTime']
            created_at = creation_time.strftime(METRICS_TIMESTAMP_FORMAT)

        data["solution"]["created_at"] = created_at
        if request_type == "delete":
            timestamp = datetime.now(timezone.utc)
            if created_at and creation_time:
                deleted_at = timestamp.strftime(METRICS_TIMESTAMP_FORMAT)
                lifespan_hours = round(
                    (timestamp - creation_time).total_seconds() / 3600, 2)
                data["solution"].update({
                    "deleted_at": deleted_at,
                    "lifespan_hours": lifespan_hours
                })
        resp = send_metrics(
            uuid=properties.get("Uuid"),
            data=data,
            solution_id=environ.get("SOLUTION_ID"),
            url=environ.get("METRICS_ENDPOINT"),
        )
        logger.info("Metrics sent with response code: %s", resp)
    except Exception as err:
        logger.warning(str(err))


def check_service_linked_role(event: events.CloudFormationCustomResourceEvent):
    """Handles checking if service linked role exist

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        dict: service linked role status

        {
            ServiceLinkedRoleExist: boolean
        }
    """
    response = {}
    iam_client = boto3.client("iam")
    if event["RequestType"] == "Create" or event["RequestType"] == "Update":
        try:
            service_linked_role = iam_client.get_role(RoleName='AWSServiceRoleForVPCTransitGateway')
            logger.info(service_linked_role)
            response = {"ServiceLinkedRoleExist": "True"}
        except ClientError as e:
            logger.exception('%s', e)
            if e.response['Error']['Code'] == 'NoSuchEntity':
                response = {"ServiceLinkedRoleExist": "False"}
            else:
                raise e
    logger.debug(response)
    return response


def send(
        event: events.CloudFormationCustomResourceEvent,
        context: LambdaContext,
        response_status,
        response_data,
        reason=None,
):
    """Sends response back to cfn

    Args:
        event (dict): event from CloudFormation on create, update or delete
        context (object): lambda context object to the handler
        response_status (string): status value sent by the custom resource provider in \
            response to an AWS CloudFormation-generated request. SUCCESS or FAILED
        response_data (dict): name-value pairs to send with the response
        reason (string, optional): reason for a failure response. Required if Status is FAILED
    """
    response_url = event["ResponseURL"]
    logger.debug("CFN response URL: %s", response_url)

    response_body = {"Status": response_status}
    msg = "See details in CloudWatch logstream: " + context.log_stream_name
    response_body["Reason"] = str(reason)[0:255] + "... " + msg
    response_body["PhysicalResourceId"] = event.get(
        "PhysicalResourceId", context.log_stream_name
    )
    response_body["StackId"] = event["StackId"]
    response_body["RequestId"] = event["RequestId"]
    response_body["LogicalResourceId"] = event["LogicalResourceId"]
    response_body["Data"] = response_data

    logger.debug("Response body: %s", str(response_body))

    json_response_body = json.dumps(response_body)
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(json_response_body)),
    }

    req = request.Request(response_url, data=json_response_body.encode('utf-8'), headers=headers, method='PUT')

    try:
        with request.urlopen(req) as response:
            # Log the status code and reason
            logger.info("CloudFormation returned status code: %s", response.reason)
    except error.HTTPError as e:
        # Handle HTTP errors
        logger.error("send(..) failed sending PUT request: %s", str(e))
        raise
    except error.URLError as e:
        # Handle URL errors (e.g., connectivity issues, invalid URL)
        logger.error("send(..) failed sending PUT request: %s", str(e.reason))
        raise

