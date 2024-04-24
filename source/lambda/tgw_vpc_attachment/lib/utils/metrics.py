# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import ssl
from datetime import datetime
from decimal import Decimal
from urllib import request, error

from aws_lambda_powertools import Logger


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


class Metrics(object):
    def __init__(self):
        self.logger = Logger(level=os.getenv('LOG_LEVEL'), service=self.__class__.__name__)

    def metrics(self, data, solution_id='SO0058', url='https://metrics.awssolutionsbuilder.com/generic'):
        try:
            send_metrics = os.environ.get('METRICS_FLAG', 'no')
            if send_metrics.lower() == 'yes':
                uuid = os.environ.get('SOLUTION_UUID')
                time_stamp = {'TimeStamp': str(datetime.utcnow().isoformat())}
                params = {'Solution': solution_id,
                          'UUID': uuid,
                          'Data': data}
                metrics = dict(time_stamp, **params)
                json_data = json.dumps(metrics, cls=DecimalEncoder)
                headers = {'content-type': 'application/json'}
                context = ssl.create_default_context()
                req = request.Request(url, data=json_data.encode('utf-8'), headers=headers, method='POST')

                try:
                    with request.urlopen(req, context=context) as response:
                        response_code = response.getcode()  # Get the response code
                        return response_code
                except error.HTTPError as e:
                    # Handle HTTP errors
                    return e.code
                except error.URLError as e:
                    # Handle URL errors (e.g., connectivity issues, invalid URL)
                    return str(e.reason)
        except Exception as err:
            self.logger.error(str(err))