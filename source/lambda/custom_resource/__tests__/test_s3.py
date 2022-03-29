# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""S3 test module"""

import pytest
from botocore.exceptions import ClientError
from moto.s3 import mock_s3
from custom_resource.lib.s3 import S3


@pytest.mark.TDD
@mock_s3
class TestClassCopyObject:
    """TDD test class for S3 copy_object calls"""

    src_bucket = "my-src-bucket"
    src_object = "/test/object"
    dest_bucket = "my-dest-bucket"
    dest_object = "/test/object"

    def test__success(self):
        """success"""
        aws_s3 = S3()

        # mock setup
        aws_s3.s3_client.create_bucket(Bucket=self.src_bucket)
        aws_s3.s3_client.create_bucket(Bucket=self.dest_bucket)
        aws_s3.s3_client.put_object(
            Bucket=self.src_bucket, Body="hello world", Key=self.src_object
        )

        aws_s3.copy_object(
            src_bucket_name=self.src_bucket,
            src_object=self.src_object,
            dest_bucket_name=self.dest_bucket,
            dest_object=self.dest_object,
        )

        # clean-up
        aws_s3.s3_client.delete_object(
            Bucket=self.src_bucket,
            Key=self.src_object,
        )
        aws_s3.s3_client.delete_object(
            Bucket=self.dest_bucket,
            Key=self.dest_object,
        )
        aws_s3.s3_client.delete_bucket(Bucket=self.src_bucket)
        aws_s3.s3_client.delete_bucket(Bucket=self.dest_bucket)

    def test__fail__resource_not_found(self):
        """fail with NoSuchBucket"""
        aws_s3 = S3()

        with pytest.raises(ClientError) as execinfo:
            aws_s3.copy_object(
                src_bucket_name=self.src_bucket,
                src_object=self.src_object,
                dest_bucket_name=self.dest_bucket,
                dest_object=self.dest_object,
            )
        assert execinfo.value.response["Error"]["Code"] == "NoSuchBucket"


@pytest.mark.TDD
@mock_s3
class TestClassPutObject:
    """TDD test class for S3 put_object calls"""

    dest_bucket = "my-dest-bucket"
    dest_object = "/test/object"

    def test__success(self):
        """success"""
        aws_s3 = S3()

        # mock setup
        aws_s3.s3_client.create_bucket(Bucket=self.dest_bucket)
        aws_s3.put_object(self.dest_bucket, self.dest_object, "hello world")

        # clean-up
        aws_s3.s3_client.delete_object(
            Bucket=self.dest_bucket,
            Key=self.dest_object,
        )
        aws_s3.s3_client.delete_bucket(Bucket=self.dest_bucket)

    def test__fail__resource_not_found(self):
        """fail with NoSuchBucket"""
        aws_s3 = S3()

        # mock setup
        with pytest.raises(ClientError) as execinfo:
            aws_s3.put_object(self.dest_bucket, self.dest_object, "hello world")
        assert execinfo.value.response["Error"]["Code"] == "NoSuchBucket"
