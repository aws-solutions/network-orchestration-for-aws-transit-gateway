# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

from lib.string_manipulation import get_delimiter


def test_colon_delimiter_type():
    peer_region = 'us-east-1'
    tag = 'PeerTgw:us-east-1'
    region = tag.split(get_delimiter('Colon (:)'))[1]
    assert region == peer_region


def test_dot_delimiter_type():
    peer_region = 'us-east-1'
    tag = 'PeerTgw.us-east-1.1'
    region = tag.split(get_delimiter('Dot (.)'))[1]
    assert region == peer_region


def test_underscore_delimiter_type():
    peer_region = 'us-east-1'
    tag = 'PeerTgw_us-east-1_2'
    region = tag.split(get_delimiter('Underscore (_)'))[1]
    assert region == peer_region


def test_pipe_delimiter_type():
    peer_region = 'us-east-1'
    tag = 'PeerTgw|us-east-1|3'
    region = tag.split(get_delimiter('Pipe (|)'))[1]
    assert region == peer_region
