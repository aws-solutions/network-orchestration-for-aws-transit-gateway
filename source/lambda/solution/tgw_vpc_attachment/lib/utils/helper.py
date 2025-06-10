# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime


def timestamp_message(message) -> str:
    return f"{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}: {message}"


def current_time() -> str:
    return str(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
