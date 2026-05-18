# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Custom resource helper test module"""

import json
import unittest
from os import environ, path
from unittest.mock import mock_open

import pytest

import boto3
from moto import mock_s3, mock_cloudfront

from solution.custom_resource.lib.console_deployment import ConsoleDeployment

TEST_REGION = "us-east-2"

RESOURCE_PROPERTIES = {
    "SrcBucket": "solutionBucker",
    "SrcPath": "stno/version",
    "ConsoleBucket": "myConsoleBucket",
    "AwsUserPoolsId": "myUserPoolId",
    "AwsUserPoolsWebClientId": "myWebClient",
    "AwsCognitoIdentityPoolId": "myCognitoIdp",
    "AwsAppsyncGraphqlEndpoint": "myAppSyncEndpoint",
    "AwsContentDeliveryBucket": "myCDNBucket",
    "AwsContentDeliveryUrl": "muCDNUrl",
    "AwsCognitoDomainPrefix": ""
}
CREATE_CONSOLE_DEPLOY = {
    "RequestType": "Create",
    "ResourceProperties": RESOURCE_PROPERTIES,
}


class TestClassConsoleDeploy(unittest.TestCase):

    def test__delete_event(self):
        """delete, does nothing"""
        # GIVEN
        console_deployment = ConsoleDeployment({}, mock_open, path.exists)

        # WHEN
        return_value = console_deployment.deploy({"RequestType": "Delete", "ResourceProperties": RESOURCE_PROPERTIES, })

        # THEN
        assert return_value == False

    def test__failed__file_not_found(self):
        """failed, manifest file not found"""
        # GIVEN
        console_deployment = ConsoleDeployment({}, mock_open, path.exists)

        # WHEN
        with pytest.raises(FileNotFoundError) as err:
            console_deployment.deploy(CREATE_CONSOLE_DEPLOY)

            # THEN
            assert str(err.value) == "console manifest file not found"

    def test__success(self):
        """success, console deploy"""
        # GIVEN
        environ["AWS_REGION"] = "my-region"

        class MockClient:
            def __init__(self):
                self.put_object_calls = 0
                self.copy_object_calls = 0

            def copy_object(self, **kwargs):
                self.copy_object_calls = self.copy_object_calls + 1

            def put_object(self, **kwargs):
                self.put_object_calls = self.put_object_calls + 1

            def list_objects_v2(self, **kwargs):
                return {"Contents": []}

            def delete_object(self, **kwargs):
                pass  # No-op for this test case (no old assets to delete)

        files = ["ui_file_1", "ui_file_2", "ui_file_3"]

        def exists_fn(_): return True

        open_fn = mock_open(read_data=json.dumps({"files": files}))

        client = MockClient()
        console_deployment = ConsoleDeployment(client, open_fn, exists_fn)

        # WHEN
        console_deployment.deploy(CREATE_CONSOLE_DEPLOY)

        # THEN
        assert client.put_object_calls == 1
        assert client.copy_object_calls == 3

    @mock_s3
    def test__success_deletes_old_assets_and_sets_cache_control(self):
        """success, console deploy deletes old assets and sets no-cache headers"""
        # GIVEN
        environ["AWS_REGION"] = TEST_REGION
        s3_client = boto3.client("s3", region_name=TEST_REGION)
        s3_client.create_bucket(Bucket="solutionBucker", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})
        s3_client.create_bucket(Bucket="myConsoleBucket", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})

        # Upload source files
        for file in ["index.html", "assets/index-NEW.js"]:
            s3_client.put_object(Bucket="solutionBucker", Key=f"stno/version/console/{file}", Body=b"content")

        # Pre-populate console bucket with old assets
        s3_client.put_object(Bucket="myConsoleBucket", Key="console/assets/index-OLD.js", Body=b"old")
        s3_client.put_object(Bucket="myConsoleBucket", Key="console/assets/stno_config.js", Body=b"config")

        files = ["index.html", "assets/index-NEW.js"]
        open_fn = mock_open(read_data=json.dumps({"files": files}))
        console_deployment = ConsoleDeployment(s3_client, open_fn, lambda _: True)

        # WHEN
        console_deployment.deploy(CREATE_CONSOLE_DEPLOY)

        # THEN - old asset deleted, stno_config.js preserved, new files copied with cache headers
        response = s3_client.list_objects_v2(Bucket="myConsoleBucket", Prefix="console/assets/")
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        assert "console/assets/index-OLD.js" not in keys
        assert "console/assets/index-NEW.js" in keys
        assert "console/assets/stno_config.js" in keys

        # Verify Cache-Control header
        head = s3_client.head_object(Bucket="myConsoleBucket", Key="console/index.html")
        assert head["CacheControl"] == "no-store, no-cache"

    @mock_s3
    @mock_cloudfront
    def test__success_invalidates_cloudfront(self):
        """success, console deploy triggers CloudFront invalidation"""
        # GIVEN
        environ["AWS_REGION"] = TEST_REGION
        s3_client = boto3.client("s3", region_name=TEST_REGION)
        cloudfront_client = boto3.client("cloudfront", region_name="us-east-1")

        s3_client.create_bucket(Bucket="solutionBucker", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})
        s3_client.create_bucket(Bucket="myConsoleBucket", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})
        s3_client.put_object(Bucket="solutionBucker", Key="stno/version/console/index.html", Body=b"content")

        # Create CloudFront distribution
        dist = cloudfront_client.create_distribution(DistributionConfig={
            "CallerReference": "test-ref",
            "Origins": {"Quantity": 1, "Items": [{"Id": "S3", "DomainName": "myConsoleBucket.s3.amazonaws.com",
                                                   "S3OriginConfig": {"OriginAccessIdentity": ""}}]},
            "DefaultCacheBehavior": {"TargetOriginId": "S3", "ViewerProtocolPolicy": "redirect-to-https",
                                     "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
                                     "TrustedSigners": {"Enabled": False, "Quantity": 0}, "MinTTL": 0},
            "Comment": "test", "Enabled": True,
        })
        distribution_id = dist["Distribution"]["Id"]

        files = ["index.html"]
        open_fn = mock_open(read_data=json.dumps({"files": files}))
        event = {
            "RequestType": "Create",
            "ResourceProperties": {**RESOURCE_PROPERTIES, "CloudFrontDistributionId": distribution_id},
        }
        console_deployment = ConsoleDeployment(s3_client, open_fn, lambda _: True, cloudfront_client)

        # WHEN
        console_deployment.deploy(event)

        # THEN
        invalidations = cloudfront_client.list_invalidations(DistributionId=distribution_id)
        assert invalidations["InvalidationList"]["Quantity"] == 1

    @mock_s3
    @mock_cloudfront
    def test__success_update_event(self):
        """success, console deploy on Update event (same flow as Create)"""
        # GIVEN
        environ["AWS_REGION"] = TEST_REGION
        s3_client = boto3.client("s3", region_name=TEST_REGION)
        cloudfront_client = boto3.client("cloudfront", region_name="us-east-1")

        s3_client.create_bucket(Bucket="solutionBucker", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})
        s3_client.create_bucket(Bucket="myConsoleBucket", CreateBucketConfiguration={"LocationConstraint": TEST_REGION})
        for file in ["index.html", "assets/index-abc123.js"]:
            s3_client.put_object(Bucket="solutionBucker", Key=f"stno/version/console/{file}", Body=b"content")

        dist = cloudfront_client.create_distribution(DistributionConfig={
            "CallerReference": "test-ref-update",
            "Origins": {"Quantity": 1, "Items": [{"Id": "S3", "DomainName": "myConsoleBucket.s3.amazonaws.com",
                                                   "S3OriginConfig": {"OriginAccessIdentity": ""}}]},
            "DefaultCacheBehavior": {"TargetOriginId": "S3", "ViewerProtocolPolicy": "redirect-to-https",
                                     "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
                                     "TrustedSigners": {"Enabled": False, "Quantity": 0}, "MinTTL": 0},
            "Comment": "test", "Enabled": True,
        })
        distribution_id = dist["Distribution"]["Id"]

        files = ["index.html", "assets/index-abc123.js"]
        open_fn = mock_open(read_data=json.dumps({"files": files}))
        event = {
            "RequestType": "Update",
            "ResourceProperties": {**RESOURCE_PROPERTIES, "CloudFrontDistributionId": distribution_id},
        }
        console_deployment = ConsoleDeployment(s3_client, open_fn, lambda _: True, cloudfront_client)

        # WHEN
        console_deployment.deploy(event)

        # THEN
        invalidations = cloudfront_client.list_invalidations(DistributionId=distribution_id)
        assert invalidations["InvalidationList"]["Quantity"] == 1
        response = s3_client.list_objects_v2(Bucket="myConsoleBucket", Prefix="console/")
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        assert "console/index.html" in keys
        assert "console/assets/index-abc123.js" in keys
