# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Solution helper module"""

from datetime import datetime
import json
import logging
import os
import re
import requests
import botocore


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


def convert_string_to_list(comma_delimited_list: str):
    """
    Converts the comma delimited list of string to a list type and skips adding
    empty strings to the list.

    Args:
        comma_delimited_list (string): comma delimited list of strings

    Returns:
        list[string]

    """
    return [
        value.strip()
        for value in comma_delimited_list.split(",")
        if (value not in [" ", ""])
    ]


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


def setup_logger(log_level):
    """function to setup root logger

    Args:
        log_level (string): log level info, debug, warn, error etc.
    """
    loglevel = logging.getLevelName(log_level.upper())
    root_logger = logging.getLogger()
    root_logger.setLevel(loglevel)

    # pylint: disable=line-too-long
    logformat = json.dumps(
        {
            "timestamp": "%(asctime)s",
            "module": "%(name)s",
            "log_level": "%(levelname)s",
            "log_message": "%(message)s",
        }
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(logformat))

    if len(root_logger.handlers) == 0:
        root_logger.addHandler(stream_handler)
    else:
        root_logger.handlers[0] = stream_handler


boto3_config = botocore.config.Config(
    retries={"max_attempts": 5, "mode": "standard"},
    user_agent_extra=os.environ.get("USER_AGENT_STRING", None),
)
