import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_sts

from tgw_vpc_attachment.__tests__.conftest import override_environment_variables
from tgw_vpc_attachment.lib.clients.ec2 import EC2
from tgw_vpc_attachment.main import lambda_handler


@mock_sts
def test_tgw_approval_required_tag_no(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']
    event = get_event(vpc_setup_with_explicit_route_table)

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    print(response)
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'


@mock_sts
def test_tgw_approval_required_tag_yes(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']
    event = get_event(vpc_setup_with_explicit_route_table)
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        os.environ['APPROVAL_KEY'],
        'yes'
    )

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response['Status'] == 'requested'


@mock_sts
def test_tgw_approval_required_tag_conditional_no_rules(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response['Status'] == 'requested'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_accept_both(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'
    assert response['Status'] == 'auto-approved'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_accept_association_reject_propagation(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_accept_association_approval_propagation(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'ApprovalRequired')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['Status'] == 'requested'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_approval_association_accept_propagation(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'ApprovalRequired')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['Status'] == 'requested'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_reject_association_accept_propagation(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_approval_required_tag_conditional_with_rule_reject_both(vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_in_ou_matched_accept(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-InOUs",
        'Root/Infrastructure, /Root/Security'
    )

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'
    assert response['Status'] == 'auto-approved'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_in_ou_not_matched_auto_reject(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')

    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-InOUs",
        'Root/Infrastructure, /Root/Security'
    )

    # ACT
    event["AccountOuPath"] = "Root/Network/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_in_ou_matched_reject(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-InOUs",
        'Root/Infrastructure, /Root/Security'
    )

    # ACT
    event["AccountOuPath"] = "Root/Infrastructure/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_in_ou__rule_matched(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-InOUs",
        'Root/Workloads'
    )

    # ACT
    event["AccountOuPath"] = "Root/Workloads/Compliance/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_in_ou__rule_matched(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-NotInOUs",
        'Root/Infrastructure, /Root/Security'
    )

    # ACT
    event["AccountOuPath"] = "Root/Network/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event}, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_not_in_ou__rule_matched(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    gateway_route_table = vpc_setup_with_explicit_route_table['transit_gateway_route_table']
    EC2().create_tags(
        gateway_route_table,
        "ApprovalRule-01-NotInOUs",
        'Root/core'
    )

    # ACT
    event["AccountOuPath"] = "Root/Network/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'
    assert response['Status'] == 'auto-approved'
    assert response['AssociationRouteTableId'] == gateway_route_table
    assert len(response['PropagationRouteTableIds']) == 1
    assert response['PropagationRouteTableIds'][0] == gateway_route_table


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_not_in_ou__rule_does_not_match(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Reject')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Accept')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-NotInOUs",
        'Root/Infrastructure, /Root/Security'
    )

    # ACT
    event["AccountOuPath"] = "Root/Security/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'yes'
    assert response['AssociationNeedsApproval'] == 'yes'
    assert response['PropagationNeedsApproval'] == 'yes'
    assert response["ConditionalApproval"] == "auto-rejected"
    assert response['Status'] == 'auto-rejected'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_not_in_ou__rule_does_not_match(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'Accept')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-NotInOUs",
        'root/core'
    )

    # ACT
    event["AccountOuPath"] = "Root/core/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'
    assert response['Status'] == 'auto-approved'


@mock_sts
def test_tgw_route_approval_required_tag_conditional_with_rule_not_in_ou__rule_does_not_match(
        vpc_setup_with_explicit_route_table):
    # ARRANGE
    override_environment_variables()
    os.environ['TGW_ID'] = vpc_setup_with_explicit_route_table['tgw_id']

    event = get_event(vpc_setup_with_explicit_route_table)
    create_conditional_tag(vpc_setup_with_explicit_route_table)
    create_association_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'ApprovalRequired')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, 'default', 'ApprovalRequired')
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '01', 'Reject')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-01-InOUs",
        'root/core'
    )
    create_association_rule_tag(vpc_setup_with_explicit_route_table, '02', 'Accept')
    create_propagation_rule_tag(vpc_setup_with_explicit_route_table, '02', 'Accept')
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        "ApprovalRule-02-InOUs",
        'root/network'
    )

    # ACT
    event["AccountOuPath"] = "Root/network/"
    response = lambda_handler({
        'params': {
            'ClassName': 'TransitGateway',
            'FunctionName': 'describe_transit_gateway_route_tables'
        },
        'event': event
    }, LambdaContext())

    # ASSERT
    assert response['ExistingAssociationRouteTableId'] == 'none'
    assert response['ApprovalRequired'] == 'no'
    assert response['Status'] == 'auto-approved'


def get_event(vpc_setup_with_explicit_route_table):
    event = {
        'RouteTableList': [vpc_setup_with_explicit_route_table['transit_gateway_route_table']],
        'AssociationRouteTableId': vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        'TransitGatewayAttachmentId': vpc_setup_with_explicit_route_table['tgw_vpc_attachment'],
        os.getenv('ASSOCIATION_TAG'): 'flat',
        os.getenv('PROPAGATION_TAG'): ['flat'],
    }
    return event


def create_conditional_tag(vpc_setup_with_explicit_route_table):
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        os.environ['APPROVAL_KEY'],
        'conditional'
    )


def create_association_rule_tag(vpc_setup_with_explicit_route_table, rule, action):
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        f"ApprovalRule-{rule}-Association",
        action
    )


def create_propagation_rule_tag(vpc_setup_with_explicit_route_table, rule, action):
    EC2().create_tags(
        vpc_setup_with_explicit_route_table['transit_gateway_route_table'],
        f"ApprovalRule-{rule}-Propagation",
        action
    )
