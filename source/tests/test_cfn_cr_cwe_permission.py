from moto.events import mock_events
import lambda_custom_resource
from lib.logger import Logger
from lib.cloud_watch_events import CloudWatchEvents
logger = Logger('info')
cwe = CloudWatchEvents(logger)
acct_list_single = ['222222222222']
acct_list_double = ['111111111111', '222222222222']
org_list = ['arn:aws:organizations::xxx:organization/o-x1y2z3']
acct_list_triple = ['111111111111', '222222222222', '333333333333']
acct_list_hybrid = ['arn:aws:organizations::xxx:organization/o-x1y2z3', '111111111111', '222222222222']
event_bus_name = 'mock-bus-name'
context = {}
event_with_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}

event_with_org_arn = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": org_list,
        "EventBusName": event_bus_name

    }
}

event_with_org_arn_and_account = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_hybrid,
        "EventBusName": event_bus_name
    }
}

event_add_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_triple,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}

event_remove_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_single,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}

event_replace_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": [
            '333333333333'
        ],
    "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}

event_same_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}

event_add_accounts_to_org_id = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_hybrid,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": org_list,
        "EventBusName": event_bus_name
    },
}

event_remove_accounts_from_org_id = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": org_list,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_hybrid,
        "EventBusName": event_bus_name
    },
}

event_replace_org_id_with_accounts = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": org_list,
        "EventBusName": event_bus_name
    },
}

event_replace_accounts_with_org_id = {
    "ResourceType": "Custom::CWEventPermissions",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "Principals": org_list,
        "EventBusName": event_bus_name
    },
    "OldResourceProperties": {
        "Principals": acct_list_double,
        "EventBusName": event_bus_name
    }
}


@mock_events
def test_create_delete_account_as_principal():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.delete(event_with_accounts, context)


@mock_events
def test_create_delete_org_id_as_principal():
    lambda_custom_resource.create(event_with_org_arn, context)
    lambda_custom_resource.delete(event_with_org_arn, context)


@mock_events
def test_create_delete_both_as_principal():
    lambda_custom_resource.create(event_with_org_arn_and_account, context)
    lambda_custom_resource.delete(event_with_org_arn_and_account, context)


@mock_events
def test_update_add_account_as_principal():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.update(event_add_accounts, context)


@mock_events
def test_update_remove_account_as_principal():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.update(event_remove_accounts, context)


@mock_events
def test_update_replace_account_as_principal():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.update(event_replace_accounts, context)


@mock_events
def test_update_same_account_as_principal():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.update(event_same_accounts, context)


@mock_events
def test_update_add_account_as_principal_to_org_id():
    lambda_custom_resource.create(event_with_org_arn, context)
    lambda_custom_resource.update(event_add_accounts_to_org_id, context)


@mock_events
def test_update_remove_account_as_principal_from_both():
    lambda_custom_resource.create(event_with_org_arn_and_account, context)
    lambda_custom_resource.update(event_remove_accounts_from_org_id, context)


@mock_events
def test_update_replace_org_id_with_accounts():
    lambda_custom_resource.create(event_with_org_arn, context)
    lambda_custom_resource.update(event_replace_org_id_with_accounts, context)


@mock_events
def test_update_replace_accounts_with_org_id():
    lambda_custom_resource.create(event_with_accounts, context)
    lambda_custom_resource.update(event_replace_accounts_with_org_id, context)
