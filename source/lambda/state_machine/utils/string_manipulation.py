###############################################################################
# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

def convert_string_to_list(comma_delimited_list: str) -> list:
    """
    Converts the comma delimited list of string to a list type and skips adding
    empty strings to the list.
    :param comma_delimited_list:
    :return: list
    """
    empty_string = ''
    return [value.strip() for value in comma_delimited_list.split(',')
            if value != empty_string]


def get_delimiter(value) -> str:
    """ match the descriptive string and return special character
    :param value: descriptive string
    :return: special character
    """
    if value.strip() == 'Colon (:)':
        return ':'
    elif value.strip() == 'Dot (.)':
        return '.'
    elif value.strip() == 'Underscore (_)':
        return '_'
    elif value.strip() == 'Pipe (|)':
        return '|'
