# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""S3 module"""

import logging
import boto3
from botocore.exceptions import ClientError
from custom_resource.lib.utils import boto3_config


class S3:
    """Class to handle S3 methods"""

    def __init__(self):
        """initialize the CloudWatchEvents object's attributes

        Args:
            None
        """
        self.logger = logging.getLogger(__name__)
        self.s3_client = boto3.client("s3", config=boto3_config)

    # pylint: disable=too-many-arguments
    def copy_object(
        self,
        src_bucket_name,
        src_object,
        dest_bucket_name,
        dest_object=None,
    ):
        """Creates a copy of an object that is already stored in Amazon S3

        Args:
            src_bucket_name (string): name of the source bucket
            src_object (string): source object prefix + key
            dest_bucket_name (string): name of the destination bucket
            dest_object (string, optional): destination object key + prefix. Defaults to None.

        Returns:
            None: copy_object api response

        Raises:
            ClientError: general exception provided by an AWS service to your Boto3 client's request
        """
        log_message = {
            "METHOD": "copy_object",
            "MESSAGE": f"copying object, source_bucket: {src_bucket_name}, object: {src_object}, destination_bucket: {dest_bucket_name}, destination_key: {dest_object}",
        }
        self.logger.debug(str(log_message))
        try:
            copy_source = {
                "Bucket": src_bucket_name,
                "Key": src_object,
            }
            if dest_object is None:
                dest_object = src_object
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket_name,
                Key=dest_object,
            )
        except ClientError as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise

    def put_object(self, dest_bucket_name, dest_object, src_data):
        """Adds an object to a S3 bucket

        Args:
            dest_bucket_name (string): bucket name to which the PUT action was initiated
            dest_object (string): object key for which the PUT action was initiated
            src_data (bytes or string): object data

        Returns:
            None: api response

        Raises:
            ClientError: general exception provided by an AWS service to your Boto3 client's request
        """
        log_message = {
            "METHOD": "put_object",
            "MESSAGE": f"putting object destination_bucket: {dest_bucket_name},\
                 destination_object: {dest_object}",
        }
        self.logger.debug(str(log_message))
        try:
            if isinstance(src_data, str):
                body = src_data
            elif isinstance(src_data, bytes):
                body = open(src_data, "rb")
            self.s3_client.put_object(
                Bucket=dest_bucket_name, Key=dest_object, Body=body
            )
        except ClientError as err:
            log_message["EXCEPTION"] = str(err)
            self.logger.error(str(log_message))
            raise
