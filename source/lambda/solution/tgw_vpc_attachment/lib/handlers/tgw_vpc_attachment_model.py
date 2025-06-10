# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import TypedDict, List, Dict

from mypy_boto3_ec2.literals import TransitGatewayAttachmentStateType


class TgwVpcAttachmentModel(TypedDict):
    detail: Dict
    source: str
    account: str
    region: str
    resources: List[str]
    time: str
    StateMachineArn: str
    TagEventSource: str
    AttachmentState: TransitGatewayAttachmentStateType
    VpcId: str
    VpcName: str
    SubnetId: str
    VpcCidr: str
    AvailabilityZone: str
    VpcTagFound: str
    AWSSpokeAccountId: str
    RouteTableId: str
    GatewayId: str
    DefaultRouteToTgwExists: str
    DestinationRouteExists: str
    AccountName: str
    AccountOuPath: str
    SubnetTagFound: str
    AttachmentTagsRequired: Dict
    TgwAttachmentExist: str
    TransitGatewayAttachmentId: str
    FoundExistingSubnetInAttachment: str
    Status: str
    Comment: str
    ConditionalApproval: str
    RouteTableList: List[str]
    ExistingAssociationRouteTableId: str
    ExistingPropagationRouteTableIds: List[str]
    UpdateAssociationRouteTableId: str
    EnablePropagationRouteTableIds: List[str]
    DisablePropagationRouteTableIds: List[str]
    PropagationRouteTableIds: List[str]
    ApprovalRequired: str
    PropagationNeedsApproval: str
    AssociationRouteTable: str
    PropagationRouteTables: str
    AssociationRouteTableId: str
    AssociationNeedsApproval: str
    AssociationState: str
    DisassociationState: str
    Action: str
    AdminAction: str
    RouteToTgw: str
    RouteTableType: str

