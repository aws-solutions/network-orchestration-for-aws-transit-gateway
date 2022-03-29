# !/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State Machine Handler module"""

import json
from datetime import datetime
from decimal import Decimal
import requests
import logging
import os


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
        self.logger = logging.getLogger(__name__)

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
                r = requests.post(url, data=json_data, headers=headers)
                code = r.status_code
                return code
        except Exception:
            pass