
from moto import mock_s3
import boto3
import botocore.exceptions
import lambda_custom_resource
from lib.logger import Logger
from lib.s3 import S3
import os

logger = Logger('critical')
s3 = S3(logger)

context = {}
event = {
    "ResourceType": "Custom::ConsoleDeploy",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "ConsoleBucket": "ConsoleBucket",
        "SrcBucket": "SrcBucket",
        "SrcPath": "SrcPath",
        "AwsProjectRegion": "aws_project_region",
        "AwsCognitoRegion": "aws_cognito_region",
        "AwsUserPoolsId": "aws_user_pools_id",
        "AwsUserPoolsWebClientId": "aws_user_pools_web_client_id",
        "AwsCognitoIdentityPoolId": "aws_cognito_identity_pool_id",
        "oauth": {},
        "AwsAppsyncGraphqlEndpoint": "aws_appsync_graphqlEndpoint",
        "AwsAppsyncRegion": "aws_appsync_region",
        "AMAZON_COGNITO_USER_POOLS": "AMAZON_COGNITO_USER_POOLS",
        "AwsContentDeliveryBucket": "aws_content_delivery_bucket",
        "AwsContentDeliveryBucketRegion": "aws_content_delivery_bucket_region",
        "AwsContentDeliveryUrl": "aws_content_delivery_url"
    }
}


@mock_s3
def test_s3ConsoleDeploy_create():
    s3_conn = boto3.resource('s3')
    s3_conn.create_bucket(Bucket='ConsoleBucket')
    s3_conn.create_bucket(Bucket='SrcBucket')
    
    file_path = os.path.join(os.path.dirname(__file__), "console-manifest.json")
    if not os.path.exists(file_path):
        open(file_path, 'w')
     
    lambda_custom_resource.create(event, context)
    
@mock_s3    
def test_s3ConsoleDeploy_update():
    s3_conn = boto3.resource('s3')
    s3_conn.create_bucket(Bucket='ConsoleBucket')
    
    lambda_custom_resource.update(event, context)



