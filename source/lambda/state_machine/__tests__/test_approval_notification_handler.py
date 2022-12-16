import os
from datetime import datetime

import boto3
import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sns, mock_ec2, mock_dynamodb
from moto.core import DEFAULT_ACCOUNT_ID
from moto.sns import sns_backends
from moto.sts import mock_sts
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ec2.type_defs import VpcTypeDef
from mypy_boto3_sns.type_defs import CreateTopicResponseTypeDef

from custom_resource.lib.utils import boto3_config
from state_machine.__tests__.conftest import override_environment_variables
from state_machine.index import lambda_handler
from state_machine.lib.clients.sts import STS


def mock_sns_topic():
    sns_client = boto3.client("sns", region_name="us-east-1")
    mock_topic: CreateTopicResponseTypeDef = sns_client.create_topic(Name="foo")
    topic_arn = mock_topic.get("TopicArn")
    os.environ['APPROVAL_NOTIFICATION'] = 'yes'
    os.environ['APPROVAL_NOTIFICATION_ARN'] = topic_arn
    return topic_arn


@mock_sns
def test_approval_notification_logged():
    # ARRANGE
    override_environment_variables()

    topic_arn = mock_sns_topic()

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'ApprovalNotification',
            'FunctionName': 'notify',
        },
        'event': {
            'Status': 'failed',
        }
    }, LambdaContext())

    # ASSERT that no notification was sent
    sns_backend = sns_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
    all_sent_notifications = sns_backend.topics[topic_arn].sent_notifications
    assert len(all_sent_notifications) == 0


@mock_sns
@mock_sts
def test_request_notification_approval_email_sent():
    # ARRANGE
    override_environment_variables()

    topic_arn = mock_sns_topic()

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'ApprovalNotification',
            'FunctionName': 'notify',
        },
        'event': {
            'Status': 'requested',
            'PropagationNeedsApproval': 'yes',
            'VpcId': 'foo',
            "Associate-with": "foo",
            "Propagate-to": ["bar"],
            'account': '111122223333'
        }
    }, LambdaContext())

    # ASSERT
    sns_backend = sns_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
    all_sent_notifications = sns_backend.topics[topic_arn].sent_notifications
    assert len(all_sent_notifications) == 1


@mock_sns
@mock_sts
def test_request_notification_approval_email_sent_missing_account_id():
    # ARRANGE
    override_environment_variables()

    sns_client = boto3.client("sns", region_name="us-east-1")
    mock_topic: CreateTopicResponseTypeDef = sns_client.create_topic(Name="foo")
    topic_arn = mock_topic.get("TopicArn")

    os.environ['APPROVAL_NOTIFICATION'] = 'yes'
    os.environ['APPROVAL_NOTIFICATION_ARN'] = topic_arn
    os.environ['STNO_CONSOLE_LINK'] = 'https://example.com'
    os.environ['TABLE_NAME'] = 'table'

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'ApprovalNotification',
            'FunctionName': 'notify',
        },
        'event': {
            'Status': 'requested',
            'AssociationNeedsApproval': 'yes',
            'VpcId': 'foo',
            "Associate-with": "foo",
            "Propagate-to": ["bar"]
        }}, LambdaContext())

    # ASSERT
    sns_backend = sns_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
    all_sent_notifications = sns_backend.topics[topic_arn].sent_notifications
    assert len(all_sent_notifications) == 1


@mock_sns
@mock_sts
@mock_ec2
def test_rejection_creates_tags():
    # ARRANGE
    override_environment_variables()

    sns_client = boto3.client("sns", region_name="us-east-1")
    mock_topic: CreateTopicResponseTypeDef = sns_client.create_topic(Name="foo")
    topic_arn = mock_topic.get("TopicArn")

    os.environ['APPROVAL_NOTIFICATION'] = 'yes'
    os.environ['APPROVAL_NOTIFICATION_ARN'] = topic_arn

    credentials = STS().assume_transit_network_execution_role('111122223333')
    ec2_client: EC2Client = boto3.client(
        "ec2",
        config=boto3_config,
        aws_access_key_id=credentials.get("AccessKeyId"),
        aws_secret_access_key=credentials.get("SecretAccessKey"),
        aws_session_token=credentials.get("SessionToken"),
    )
    vpc: VpcTypeDef = ec2_client.create_vpc(
        CidrBlock='10.0.0.0/24'
    )['Vpc']

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'ApprovalNotification',
            'FunctionName': 'notify',
        },
        'event': {
            'Status': 'auto-rejected',
            'AssociationNeedsApproval': 'yes',
            'PropagationNeedsApproval': 'yes',
            'VpcId': vpc['VpcId'],
            "Associate-with": "foo",
            "Propagate-to": ["bar"],
            'account': '111122223333'
        }
    }, LambdaContext())

    # ASSERT
    tags = ec2_client.describe_tags()
    assert len(tags) == 2


@mock_sns
def test_vpc_doesnt_exist_logs_error_quietly():
    # ARRANGE
    override_environment_variables()

    sns_client = boto3.client("sns", region_name="us-east-1")
    mock_topic: CreateTopicResponseTypeDef = sns_client.create_topic(Name="foo")
    topic_arn = mock_topic.get("TopicArn")

    os.environ['APPROVAL_NOTIFICATION'] = 'yes'
    os.environ['APPROVAL_NOTIFICATION_ARN'] = topic_arn

    # ACT
    lambda_handler({
        'params': {
            'ClassName': 'ApprovalNotification',
            'FunctionName': 'notify',
        },
        'event': {
            'Status': 'auto-rejected',
            'AssociationNeedsApproval': 'yes',
            'PropagationNeedsApproval': 'yes',
            'VpcId': 'doesnt-exist',
            "Associate-with": "foo",
            "Propagate-to": ["bar"],
            'account': '444455556666'
        }
    }, LambdaContext())

    # ASSERT
    # no exception


@mock_sns
@mock_sts
@mock_dynamodb
def test_topic_doesnt_exist(dynamodb_table):
    # ARRANGE
    override_environment_variables()

    os.environ['APPROVAL_NOTIFICATION'] = 'yes'
    os.environ['APPROVAL_NOTIFICATION_ARN'] = 'doesnt-exist'

    # ACT
    with pytest.raises(Exception):
        lambda_handler({
            'params': {
                'ClassName': 'ApprovalNotification',
                'FunctionName': 'notify',
            },
            'event': {
                'Status': 'requested',
                'AssociationNeedsApproval': 'yes',
                'VpcId': 'foo',
                "Associate-with": "foo",
                "Propagate-to": ["bar"],
                'time': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }}, LambdaContext())

    # ASSERT
