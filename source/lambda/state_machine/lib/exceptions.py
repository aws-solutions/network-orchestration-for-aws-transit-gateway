# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Exceptions module"""


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
