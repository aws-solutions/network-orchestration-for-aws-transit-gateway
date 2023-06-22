# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from functools import wraps
from os import getenv
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
logger = Logger(service='exception_handler', level=getenv('LOG_LEVEL'))


def resource_exception_handler(func):
    @wraps(func)
    def wrapper_func(self, *args, **kwargs):
        try:
            response = func(self, *args, **kwargs)
        except ClientError as err:
            exception_codes = [
                'IncorrectState',
                'InsufficientSubnetsException',
                'OptInRequired',
                'DuplicateSubnetsInSameZone'
            ]
            if err.response['Error']['Code'] in exception_codes:
                logger.error(str(err))
                return {'Error': err.response['Error']['Code']}
            else:
                logger.error(err)
                raise err
        return response
    return wrapper_func


def service_exception_handler(func):
    @wraps(func)
    def wrapper_func(self, *args, **kwargs):
        try:
            response = func(self, *args, **kwargs)
        except ClientError as err:
            if err.response['Error']['Code'] == "InvalidVpcID.NotFound" \
                    or err.response['Error']['Code'] == "InvalidSubnetID.NotFound":
                raise ResourceNotFoundException(err)
            elif err.response['Error']['Code'] == "DuplicateTransitGatewayAttachment":
                raise AttachmentCreationInProgressException(err)
            elif err.response['Error']['Code'] == "TransitGatewayRouteTablePropagation.Duplicate"\
                    or err.response['Error']['Code'] == "Resource.AlreadyAssociated":
                raise AlreadyConfiguredException(err)
            elif err.response['Error']['Code'] == "IncorrectState":
                raise ResourceBusyException(err)
            else:
                logger.error(err)
                raise err
        return response
    return wrapper_func


class ResourceNotFoundException(Exception):
    # Thrown when a resource is missing, i.e. when a VPC
    # or subnet gets deleted. This is caught by the step function.
    pass


class AttachmentCreationInProgressException(Exception):
    # Thrown when a new TGW attachment was supposed to be created
    # but it failed because another step function execution that is happening
    # in parallel is already creating the TGW attachment
    pass


class AlreadyConfiguredException(Exception):
    # Thrown when an action was performed that was already done before
    pass


class ResourceBusyException(Exception):
    # Thrown when a resource is busy, and needs to be tried again later.
    pass


class RouteTableNotFoundException(Exception):
    # Thrown when a named route table (association or propagation) was not found
    pass
