from moto.events import mock_events
from lib.logger import Logger
from lib.cloud_watch_events import CloudWatchEvents
logger = Logger('critical')
cwe = CloudWatchEvents(logger)
import json


@mock_events
def test_permissions():
    event_bus_name = 'mock-bus-name'

    # put_permission(principal, statement_id, condition=None)
    cwe.put_permission('111111111111', 'Account1', event_bus_name)
    cwe.put_permission('222222222222', 'Account2', event_bus_name)

    resp = cwe.describe_event_bus(event_bus_name)
    resp_policy = json.loads(resp['Policy'])
    assert len(resp_policy['Statement']) == 2

    cwe.remove_permission('Account2', event_bus_name)

    resp = cwe.describe_event_bus(event_bus_name)
    resp_policy = json.loads(resp['Policy'])
    assert len(resp_policy['Statement']) == 1
    assert resp_policy['Statement'][0]['Sid'] == 'Account1'
