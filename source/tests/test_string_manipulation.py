##############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Apache License, Version 2.0 (the "License").           #
#  You may not use this file except in compliance                            #
#  with the License. A copy of the License is located at                     #
#                                                                            #
#      http://www.apache.org/licenses/LICENSE-2.0                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is             #
#  distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  #
#  KIND, express or implied. See the License for the specific language       #
#  governing permissions  and limitations under the License.                 #
##############################################################################
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
