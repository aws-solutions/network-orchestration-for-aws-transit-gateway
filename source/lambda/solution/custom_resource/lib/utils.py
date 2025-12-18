# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

import json
import os
import re
from datetime import datetime, timezone
from urllib import request, error

import botocore

METRICS_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"  # This is the required format for the metrics API. Any changes should be taken with care


def sanitize(name, space_allowed=False, replace_with_character="_"):
    """sanitizes string to remove unwanted characters

    Args:
        name ([type]): name to sanitize
        space_allowed (bool, optional): identify if space allowed in sanitized string.\
             Defaults to False.
        replace_with_character (str, optional): replacement character. Defaults to "_".

    Returns:
        string: sanitized string
    """
    if space_allowed:
        sanitized_name = re.sub(
            r"([^\sa-zA-Z0-9._-])", replace_with_character, name
        )
    else:
        sanitized_name = re.sub(
            r"([^a-zA-Z0-9._-])", replace_with_character, name
        )
    return sanitized_name


def send_metrics(
    uuid,
    data,
    solution_id,
    url="https://metrics.awssolutionsbuilder.com/generic",
):
    """sends metric to aws-solutions

    Args:
        uuid (string): unique id for metrics collection
        data (dict): usage metrics from the solution
        solution_id (string): solution id
        url (str, optional): aws-solutions endpoint. \
            Defaults to "https://metrics.awssolutionsbuilder.com/generic".

    Returns:
        int: request code
    """
    time_stamp = {
        "TimeStamp": datetime.now(timezone.utc).strftime(METRICS_TIMESTAMP_FORMAT)
    }  # Date and time instant in a java.sql.Timestamp compatible format,
    params = {
        "Solution": solution_id, 
        "UUID": uuid, 
        "AccountId": os.environ.get("AWS_ACCOUNT_ID", "unknown"),
        "StackId": os.environ.get("STACK_ID", "unknown"),
        "Data": data
    }
    metrics = dict(time_stamp, **params)
    json_data = json.dumps(metrics)
    headers = {"Content-Type": "application/json"}

    # Prepare the data and headers for the POST request
    data = json_data.encode('utf-8')  # Encode the data to bytes
    req = request.Request(url, data=data, headers=headers, method='POST')

    # Execute the request and handle the response
    try:
        with request.urlopen(req) as response:
            code = response.getcode()  # Get the response code
            return code
    except error.HTTPError as e:
        # If an HTTP error occurs, return the HTTP error code
        return e.code
    except error.URLError as e:
        # Handle other URL errors and re-raise them
        raise ConnectionError(f"Error during POST request: {e.reason}")


boto3_config = botocore.config.Config(
    retries={"max_attempts": 5, "mode": "standard"},
    user_agent_extra=os.environ.get("USER_AGENT_STRING", None),
)
