# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

import json
import os
import re
from datetime import datetime

import botocore
import requests


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
        uuid (string): unique id to make metrics anonymous
        data (dict): usage metrics from the solution
        solution_id (string): solution id
        url (str, optional): aws-solutions endpoint. \
            Defaults to "https://metrics.awssolutionsbuilder.com/generic".

    Returns:
        int: request code
    """
    time_stamp = {
        "TimeStamp": str(datetime.utcnow().isoformat())
        .replace("T", " ")
        .replace("Z", "")
    }  # Date and time instant in a java.sql.Timestamp compatible format,
    params = {"Solution": solution_id, "UUID": uuid, "Data": data}
    metrics = dict(time_stamp, **params)
    json_data = json.dumps(metrics)
    headers = {"content-type": "application/json"}
    req = requests.post(url, data=json_data, headers=headers)
    code = req.status_code
    return code


boto3_config = botocore.config.Config(
    retries={"max_attempts": 5, "mode": "standard"},
    user_agent_extra=os.environ.get("USER_AGENT_STRING", None),
)
