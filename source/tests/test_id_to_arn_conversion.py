from lambda_custom_resource import create, update, delete
from lib.logger import Logger
import pytest

logger = Logger('info')

event = {
    "RequestType": "Create",
    "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function:TransitNetworkOrchestratorCRLambda",
    "ResponseURL": "https://cloudformation-custom-resource-response-euwest1.s3-eu-west-1.amazonaws.com/arn",
    "StackId": "arn:aws:cloudformation:eu-west-1:999999:stack/StackSet-STNO-hub",
    "RequestId": "3d249554-871e-4a25-a46c-d3a7027d3c2f",
    "LogicalResourceId": "TestResourceId",
    "ResourceType": "Custom::GetPrefixListArns",
    "PhysicalResourceId": "80afcad19ddf557011f84a6004bcb96f",
    "ResourceProperties": {
        "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function:TransitNetworkOrchestratorCRLambda",
        "PrefixListIds": "pl-abcd1234, pl-efgh5678",
        "AccountId": "999999"
    }
}

event_with_extra_comma = {
    "RequestType": "Create",
    "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function:TransitNetworkOrchestratorCRLambda",
    "ResponseURL": "https://cloudformation-custom-resource-response-euwest1.s3-eu-west-1.amazonaws.com/arn",
    "StackId": "arn:aws:cloudformation:eu-west-1:999999:stack/StackSet-STNO-hub",
    "RequestId": "3d249554-871e-4a25-a46c-d3a7027d3c2f",
    "LogicalResourceId": "TestResourceId",
    "ResourceType": "Custom::GetPrefixListArns",
    "PhysicalResourceId": "80afcad19ddf557011f84a6004bcb96f",
    "ResourceProperties": {
        "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function:TransitNetworkOrchestratorCRLambda",
        "PrefixListIds": "pl-abcd1234, pl-efgh5678",
        "AccountId": "999999"
    }
}

event_no_values = {
    "RequestType": "Create",
    "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function:TransitNetworkOrchestratorCRLambda",
    "ResponseURL": "https://cloudformation-custom-resource-response-euwest1.s3-eu-west-1.amazonaws.com/arn",
    "StackId": "arn:aws:cloudformation:eu-west-1:999999:stack/StackSet-STNO-hub",
    "RequestId": "3d249554-871e-4a25-a46c-d3a7027d3c2f",
    "LogicalResourceId": "TestResourceId",
    "ResourceType": "Custom::GetPrefixListArns",
    "ResourceProperties": {
        "ServiceToken": "arn:aws:lambda:eu-west-1:999999:function"
                        ":TransitNetworkOrchestratorCRLambda",
        "PrefixListIds": "",
        "AccountId": "999999"
    }
}

context = {}


def test_create_get_prefix_list_arns():
    arn_list = create(event, context)
    logger.info(arn_list)
    for arn in arn_list[1].get('PrefixListArns'):
        logger.info(arn)
        assert arn.startswith('arn:aws:ec2')


def test_no_empty_string_in_prefix_list_arns():
    arn_list = create(event_with_extra_comma, context)
    logger.info(arn_list)
    empty_string = ''
    for arn in arn_list[1].get('PrefixListArns'):
        logger.info(arn)
        assert empty_string != arn.split('/')[1]


def test_create_empty_get_prefix_list_arns():
    with pytest.raises(ValueError, match=r"STNO CFN Parameter Missing: You must"
                                         r" provide at least one valid prefix "
                                         r"list id."):
        create(event_no_values, context)


def test_update_get_prefix_list_arns():
    arn_list = update(event, context)
    logger.info(arn_list)
    for arn in arn_list[1].get('PrefixListArns'):
        logger.info(arn)
        assert arn.startswith('arn:aws:ec2')


def test_delete_get_prefix_list_arns():
    response = delete(event, context)
    assert response is None
