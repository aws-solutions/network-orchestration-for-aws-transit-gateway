# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_lambda_powertools import Logger

from solution.tgw_vpc_attachment.lib.utils.list_utils import convert_string_to_list_with_no_whitespaces

logger = Logger('info')


def test_convert_string_to_sorted_list_with_no_whitespaces():
    # ARRANGE
    string1 = 'xxxxx'
    string2 = 'yyyyy'
    string3 = 'zzzzz'
    string = f'{string1}, {string3}, {string2}  '

    # ACT
    converted_list = convert_string_to_list_with_no_whitespaces(string)

    # ASSERT
    assert string1 in converted_list
    assert string2 in converted_list
    assert string3 in converted_list
    assert string not in converted_list
    # test sorted and no whitespace
    assert [string1, string3, string2] == converted_list


def test_convert_empty_string_to_empty_list():
    # ARRANGE
    empty_string = ''

    # ACT
    converted_list = convert_string_to_list_with_no_whitespaces(empty_string)

    # ASSERT
    assert [] == converted_list

