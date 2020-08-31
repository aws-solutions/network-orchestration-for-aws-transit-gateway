###############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.    #
#                                                                             #
#  Licensed under the Apache License, Version 2.0 (the "License").            #
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at                                        #
#                                                                             #
#      http://www.apache.org/licenses/LICENSE-2.0                             #
#                                                                             #
#  or in the "license" file accompanying this file. This file is distributed  #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express #
#  or implied. See the License for the specific language governing permissions#
#  and limitations under the License.                                         #
###############################################################################


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
