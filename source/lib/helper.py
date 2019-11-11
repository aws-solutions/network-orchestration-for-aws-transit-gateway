######################################################################################################################Apache License, Version 2.0
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import re
import boto3
from os import environ
from datetime import datetime


def sanitize(name, space_allowed=False, replace_with_character='_'):
    # This function will replace any character other than [a-zA-Z0-9._-] with '_'
    if space_allowed:
        sanitized_name = re.sub(r'([^\sa-zA-Z0-9._-])', replace_with_character, name)
    else:
        sanitized_name = re.sub(r'([^a-zA-Z0-9._-])', replace_with_character, name)
    return sanitized_name


def trim_length(string, length):
    if len(string) > length:
        return string[:length]
    else:
        return string


# Getting Service regions
def get_available_regions(service_name):
    """ Returns list of regions
    Example: ['ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'ap-southeast-1', 'ap-southeast-2',
     'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-east-1',
      'us-east-2', 'us-west-1', 'us-west-2']
    """
    session = boto3.session.Session()
    return session.get_available_regions(service_name)


def get_region():
    return environ.get('AWS_REGION')


def get_endpoint(service_name):
    return "https://%s.%s.amazonaws.com" % (service_name, environ.get('AWS_REGION'))


def timestamp_message(message):
    return "%s: %s" % (datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), message)


def current_time():
    return str(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))