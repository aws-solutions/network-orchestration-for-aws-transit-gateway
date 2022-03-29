# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

from datetime import datetime


def timestamp_message(message):
    """[summary]

    Args:
        message ([type]): [description]

    Returns:
        [type]: [description]
    """
    return f"{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}: {message}"


def current_time():
    """[summary]

    Returns:
        [type]: [description]
    """
    return str(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
