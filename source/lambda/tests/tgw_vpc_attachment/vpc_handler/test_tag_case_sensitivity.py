# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
from moto import mock_ec2, mock_sts
from solution.tgw_vpc_attachment.lib.handlers.vpc_handler import VPCTagManager

@mock_ec2
@mock_sts
def test_preserve_tag_case_sensitivity():
    # Arrange
    os.environ["VPC_TAGS_FOR_ATTACHMENT"] = "costcenter, environment" # provided through cloudformation parameter input
    
    # Act
    vpc_tag_manager = VPCTagManager({})
    
    # Update event with VPC details, Key, Value coming from describe calls on VPC
    vpc_tag_manager._match_keys_with_tag('CostCenter','CC-01') 
    vpc_tag_manager._match_keys_with_tag('Environment','dev')
    updated_event = vpc_tag_manager.event

    # Assert
    assert 'AttachmentTagsRequired' in updated_event
    assert 'CostCenter' in updated_event['AttachmentTagsRequired']
    assert 'Environment' in updated_event['AttachmentTagsRequired']
    
    assert updated_event['AttachmentTagsRequired']['CostCenter'] == 'CC-01'
    assert updated_event['AttachmentTagsRequired']['Environment'] == 'dev'
    
    assert 'costcenter' not in updated_event['AttachmentTagsRequired']
    assert 'environment' not in updated_event['AttachmentTagsRequired']
    