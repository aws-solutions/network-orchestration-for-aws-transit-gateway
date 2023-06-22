# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from typing import List



def convert_string_to_list_with_no_whitespaces(_string, delimiter=',') -> list:
    string = _string.replace(' ', '')
    if string == '':
        return []
    else:
        return string.split(delimiter)
