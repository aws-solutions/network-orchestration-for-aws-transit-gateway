######################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
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

#!/bin/python

import boto3
import inspect


class S3(object):
    def __init__(self, logger, **kwargs):
        self.logger = logger
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up S3 BOTO3 Client with default credentials")
                self.s3_client = boto3.client('s3')
            else:
                logger.debug("Setting up S3 BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                self.s3_client = boto3.client('s3',
                                               aws_access_key_id=cred.get('AccessKeyId'),
                                               aws_secret_access_key=cred.get('SecretAccessKey'),
                                               aws_session_token=cred.get('SessionToken')
                                               )
        else:
            logger.info("There were no keyworded variables passed.")
            self.s3_client = boto3.client('s3')

    def get_bucket_policy(self, bucket_name):
        try:
            response = self.s3_client.get_bucket_policy(
                Bucket=bucket_name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def put_bucket_policy(self, bucket_name, bucket_policy):
        try:
            response = self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=bucket_policy
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def upload_file(self, bucket_name, local_file_location, remote_file_location):
        try:
            s3 = boto3.resource('s3')
            s3.Bucket(bucket_name).upload_file(local_file_location, remote_file_location)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def download_file(self, bucket_name, remote_file_location, local_file_location):
        try:
            s3 = boto3.resource('s3')
            s3.Bucket(bucket_name).download_file(remote_file_location, local_file_location)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def put_bucket_encryption(self, bucket_name, key_id):
        try:
            self.s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'aws:kms',
                                'KMSMasterKeyID': key_id
                            }
                        },
                    ]
                }
            )

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
    
    def copy_object(self, src_bucket_name, key_prefix, src_object_name, dest_bucket_name, dest_object_name=None):
        try:
            # Construct source bucket/object parameter
            copy_source = {'Bucket': src_bucket_name, 'Key': key_prefix + src_object_name}
            if dest_object_name is None:
                dest_object_name = src_object_name
            self.s3_client.copy_object(CopySource=copy_source, Bucket=dest_bucket_name, Key=dest_object_name)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
    
    def put_object(self, dest_bucket_name, dest_object_name, src_data):
        try:
            # Construct Body= parameter
            if isinstance(src_data, str):
                object_data = src_data
            elif isinstance(src_data, bytes):
                object_data = open(src_data, 'rb')
            self.s3_client.put_object(Bucket=dest_bucket_name, Key=dest_object_name, Body=object_data)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise