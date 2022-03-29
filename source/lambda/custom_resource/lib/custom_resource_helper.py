# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource helper module"""

import threading
from os import environ, path
import time
import json
from uuid import uuid4
import logging
import requests
from custom_resource.lib.step_functions import StepFunctions
from custom_resource.lib.cloudwatch_events import CloudWatchEvents
from custom_resource.lib.s3 import S3
from custom_resource.lib.utils import (
    sanitize,
    send_metrics,
    convert_string_to_list,
)

logger = logging.getLogger(__name__)


def trigger_sm(event, context):
    """Handler for triggering step function execution

    Args:
        event (dict): lambda triggering event
        context: context from the lambda handler

    Returns:
        None
    """
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
            resource_type = (
                    account_id
                    + "-"
                    + event.get("detail", {}).get("resource-type")
                    + "-tagged"
            )
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


def timeout(event, context):
    """_summary_

    Args:
        event (_type_): _description_
        context (_type_): _description_
    """
    logger.error("Execution is about to time out, sending failure message")
    send(event, context, "FAILED", {}, "Execution timed out")


def cfn_handler(event, context):
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

    # Setup timer to catch timeouts
    timer = threading.Timer(
        (context.get_remaining_time_in_millis() / 1000.00) - 0.5,
        timeout,
        args=[event, context, logger],
    )
    timer.start()
    log_message[
        "MESSAGE"
    ] = f"{event['RequestType']} for {event['ResourceType']}"
    logger.debug(str(log_message))
    try:
        if event["ResourceType"] == "Custom::CreateUUID":
            response_data = handle_uuid(event)

        if event["ResourceType"] == "Custom::CWEventPermissions":
            handle_cwe_permissions(event)

        if event["ResourceType"] == "Custom::ConsoleDeploy":
            handle_console_deploy(event)

        if event["ResourceType"] == "Custom::GetPrefixListArns":
            response_data = handle_prefix(event)

        if event["ResourceType"] == "Custom::SendCFNParameters":
            handle_metrics(event)

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


def handle_uuid(event):
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


def handle_cwe_permissions(event):
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
        for principal in principal_list:
            cwe.remove_permission(principal, event_bus_name)
    if request_type == "Update":
        old_properties = event.get("OldResourceProperties")
        old_principal_list = old_properties.get("Principals")
        delete_list = list(set(old_principal_list) - set(principal_list))
        for principal in delete_list:
            cwe.remove_permission(principal, event_bus_name)
        for principal in principal_list:
            cwe.put_permission(principal, event_bus_name)


def handle_console_deploy(event):
    """Handler for STNO web ui deployment

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        None
    """
    if event["RequestType"] == "Create" or event["RequestType"] == "Update":
        s3client = S3()

        properties = event["ResourceProperties"]
        file_path = path.join(
            path.dirname(__file__), "../../console-manifest.json"
        )
        logger.debug("file path for console manifest: %s", file_path)
        if path.exists(file_path):
            with open(file_path, "r") as json_data:
                data = json.load(json_data)

            destination_bucket = properties.get("ConsoleBucket")
            source_bucket = properties.get("SrcBucket")
            key_prefix = properties.get("SrcPath") + "/"

            for file in data["files"]:
                key = "console/" + file
                s3client.copy_object(
                    src_bucket_name=source_bucket,
                    src_object=key_prefix + key,
                    dest_bucket_name=destination_bucket,
                    dest_object=key,
                )

            # geenrating config file
            stno_config = {
                "aws_project_region": environ.get("AWS_REGION"),
                "aws_cognito_region": environ.get("AWS_REGION"),
                "aws_user_pools_id": properties.get("AwsUserPoolsId"),
                "aws_user_pools_web_client_id": properties.get(
                    "AwsUserPoolsWebClientId"
                ),
                "aws_cognito_identity_pool_id": properties.get(
                    "AwsCognitoIdentityPoolId"
                ),
                "oauth": {},
                "aws_appsync_graphqlEndpoint": properties.get(
                    "AwsAppsyncGraphqlEndpoint"
                ),
                "aws_appsync_region": environ.get("AWS_REGION"),
                "aws_appsync_authenticationType": "AMAZON_COGNITO_USER_POOLS",
                "aws_content_delivery_bucket": properties.get(
                    "AwsContentDeliveryBucket"
                ),
                "aws_content_delivery_bucket_region": environ.get("AWS_REGION"),
                "aws_content_delivery_url": properties.get(
                    "AwsContentDeliveryUrl"
                ),
            }

            configurations = (
                    "const stno_config = " + json.dumps(stno_config) + ";"
            )
            console_bucket = properties.get("ConsoleBucket")
            key = "console/assets/stno_config.js"

            s3client.put_object(console_bucket, key, configurations)
        else:
            logger.error("console manifest file not found")
            raise FileNotFoundError("console manifest file not found")


def handle_prefix(event):
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
        list_of_prefix_list_ids = convert_string_to_list(prefix_list)
        list_of_prefix_list_arns = []
        if len(list_of_prefix_list_ids) == 0:
            raise ValueError(
                "STNO CFN Parameter Missing: You must "
                "provide at least one valid prefix list id."
            )
        for prefix_list_id in list_of_prefix_list_ids:
            arn = f"arn:aws:ec2:{environ.get('AWS_REGION')}:{account_id}:prefix-list/{prefix_list_id}"
            list_of_prefix_list_arns.append(arn)
        response = {"PrefixListArns": list_of_prefix_list_arns}
    return response


def handle_metrics(event):
    """Handles sending launch parameters to aws-solutions

    Args:
        event (dict): event from CloudFormation on create, update or delete

    Returns:
        None
    """
    if environ.get("SEND_METRIC") == "Yes" and (
            event["RequestType"] == "Create" or event["RequestType"] == "Delete"
    ):
        properties = event["ResourceProperties"]
        data = {
            "PrincipalType": properties.get("PrincipalType"),
            "ApprovalNotificationFlag": properties.get("ApprovalNotification"),
            "AuditTrailRetentionPeriod": properties.get(
                "AuditTrailRetentionPeriod"
            ),
            "DefaultRoute": properties.get("DefaultRoute"),
            "Region": environ.get("AWS_REGION"),
            "SolutionVersion": environ.get("SOLUTION_VERSION"),
            "Event": f"Solution_{event['RequestType']}",
            "CreatedNewTransitGateway": properties.get(
                "CreatedNewTransitGateway"
            ),
        }
        try:
            resp = send_metrics(
                uuid=properties.get("Uuid"),
                data=data,
                solution_id=environ.get("SOLUTION_ID"),
                url=environ.get("METRICS_ENDPOINT"),
            )
            logger.info("Metrics sent with response code: %s", resp)
        except Exception as err:
            logger.warning(str(err))


def send(
        event,
        context,
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

    response_body = {}
    response_body["Status"] = response_status
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
        "content-type": "",
        "content-length": str(len(json_response_body)),
    }

    try:
        response = requests.put(
            response_url, data=json_response_body, headers=headers
        )
        logger.info("CloudFormation returned status code: %s", response.reason)
    except Exception as err:
        logger.error("send(..) failed executing requests.put(..): %s", str(err))
        raise
