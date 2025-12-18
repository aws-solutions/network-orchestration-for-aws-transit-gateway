#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for MetricsCollector class"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from moto import mock_ec2, mock_cloudwatch

from solution.metrics_collector.handler import MetricsCollector


@mock_ec2
@mock_cloudwatch
class TestMetricsCollector:
    """Test cases for MetricsCollector class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_logger = Mock()
        self.test_event = {"source": "aws.events"}
        self.metrics_collector = MetricsCollector(self.test_event, self.mock_logger)

    def test_init(self):
        """Test MetricsCollector initialization"""
        assert self.metrics_collector.event == self.test_event
        assert self.metrics_collector.logger == self.mock_logger
        assert self.metrics_collector.tgw_id == "tgw-0123456789abcdef0"
        assert self.metrics_collector.solution_uuid is not None

    def test_get_solution_tgw_id_success(self):
        """Test successful TGW ID retrieval from environment"""
        tgw_id = self.metrics_collector._get_solution_tgw_id()
        assert tgw_id == "tgw-0123456789abcdef0"

    @patch.dict('os.environ', {}, clear=True)
    def test_get_solution_tgw_id_missing(self):
        """Test TGW ID retrieval when environment variable is missing"""
        with pytest.raises(ValueError, match="TGW_ID environment variable not set"):
            MetricsCollector({}, Mock())

    @mock_ec2
    def test_get_tgw_attachments_single_page(self):
        """Test getting TGW attachments with single page response"""
        # Mock EC2 client response
        mock_response = {
            'TransitGatewayVpcAttachments': [
                {
                    'TransitGatewayAttachmentId': 'tgw-attach-123',
                    'VpcId': 'vpc-123',
                    'State': 'available'
                }
            ]
        }
        
        with patch.object(self.metrics_collector.ec2_client, 'describe_transit_gateway_vpc_attachments', return_value=mock_response):
            attachments = self.metrics_collector._get_tgw_attachments("tgw-123")
            
            assert len(attachments) == 1
            assert attachments[0]['TransitGatewayAttachmentId'] == 'tgw-attach-123'

    @mock_ec2
    def test_get_tgw_attachments_multiple_pages(self):
        """Test getting TGW attachments with pagination"""
        # Mock paginated responses
        page1_response = {
            'TransitGatewayVpcAttachments': [
                {'TransitGatewayAttachmentId': 'tgw-attach-1', 'VpcId': 'vpc-1', 'State': 'available'}
            ],
            'NextToken': 'token123'
        }
        
        page2_response = {
            'TransitGatewayVpcAttachments': [
                {'TransitGatewayAttachmentId': 'tgw-attach-2', 'VpcId': 'vpc-2', 'State': 'available'}
            ]
        }
        
        with patch.object(self.metrics_collector.ec2_client, 'describe_transit_gateway_vpc_attachments', side_effect=[page1_response, page2_response]):
            attachments = self.metrics_collector._get_tgw_attachments("tgw-123")
            
            assert len(attachments) == 2
            assert attachments[0]['TransitGatewayAttachmentId'] == 'tgw-attach-1'
            assert attachments[1]['TransitGatewayAttachmentId'] == 'tgw-attach-2'

    @mock_cloudwatch
    def test_collect_batch_metrics(self):
        """Test collecting metrics for a batch of attachments"""
        # Mock attachments
        attachments = [
            {
                'TransitGatewayAttachmentId': 'tgw-attach-123',
                'VpcId': 'vpc-123'
            }
        ]
        
        # Mock CloudWatch response
        mock_cw_response = {
            'MetricDataResults': [
                {'Id': 'att_0_bytes_in', 'Values': [1000]},
                {'Id': 'att_0_bytes_out', 'Values': [2000]},
                {'Id': 'att_0_drops_packets', 'Values': [10]},
                {'Id': 'att_0_drops_bytes', 'Values': [100]}
            ]
        }
        
        with patch.object(self.metrics_collector.cloudwatch_client, 'get_metric_data', return_value=mock_cw_response):
            with patch.object(self.metrics_collector, '_emit_attachment_metrics') as mock_emit:
                self.metrics_collector._collect_batch_metrics(attachments)
                
                # Verify emit was called with correct parameters
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args[0]
                assert call_args[0] == attachments[0]  
                assert call_args[2] == 0  

    def test_emit_attachment_metrics(self):
        """Test emitting metrics for a single attachment"""
        attachment = {
            'TransitGatewayAttachmentId': 'tgw-attach-123',
            'VpcId': 'vpc-123'
        }
        
        cloudwatch_response = {
            'MetricDataResults': [
                {'Id': 'att_0_bytes_in', 'Values': [1000]},
                {'Id': 'att_0_bytes_out', 'Values': [2000]},
                {'Id': 'att_0_drops_packets', 'Values': [10]},
                {'Id': 'att_0_drops_bytes', 'Values': [100]}
            ]
        }
        
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        
        with patch('solution.metrics_collector.handler.Metrics') as mock_metrics_class:
            mock_metrics_instance = Mock()
            mock_metrics_class.return_value = mock_metrics_instance
            
            self.metrics_collector._emit_attachment_metrics(
                attachment, cloudwatch_response, 0, start_time, end_time
            )
            
            # Verify metrics were sent
            mock_metrics_instance.metrics.assert_called_once()
            payload = mock_metrics_instance.metrics.call_args[0][0]
            
            # Verify payload structure
            assert payload['solution'] == 'SO0058'
            assert payload['account_id'] == '123456789012'
            assert payload['data']['event']['type'] == 'tgw_attachment'
            assert payload['data']['event']['action'] == 'network_metrics'
            assert payload['data']['metrics']['bytes_in'] == 1000
            assert payload['data']['metrics']['bytes_out'] == 2000
            assert payload['data']['metrics']['drops_packets'] == 10
            assert payload['data']['metrics']['drops_bytes'] == 100

    @mock_cloudwatch
    def test_collect_tgw_metrics(self):
        """Test collecting TGW-level metrics"""
        # Mock CloudWatch response
        mock_cw_response = {
            'MetricDataResults': [
                {'Id': 'tgw_bytes_in', 'Values': [5000]},
                {'Id': 'tgw_bytes_out', 'Values': [6000]},
                {'Id': 'tgw_drops_packets', 'Values': [50]},
                {'Id': 'tgw_drops_bytes', 'Values': [500]}
            ]
        }
        
        mock_ec2_response = {
            'TransitGateways': [
                {
                    'TransitGatewayId': 'tgw-0123456789abcdef0',
                    'CreationTime': datetime.now(timezone.utc)
                }
            ]
        }
        
        with patch.object(self.metrics_collector.ec2_client, 'describe_transit_gateways', return_value=mock_ec2_response):
            with patch.object(self.metrics_collector.cloudwatch_client, 'get_metric_data', return_value=mock_cw_response):
                with patch('solution.metrics_collector.handler.Metrics') as mock_metrics_class:
                    mock_metrics_instance = Mock()
                    mock_metrics_class.return_value = mock_metrics_instance
                    
                    self.metrics_collector._collect_tgw_metrics()
                    
                    # Verify metrics were sent
                    mock_metrics_instance.metrics.assert_called_once()
                    payload = mock_metrics_instance.metrics.call_args[0][0]
                    
                    # Verify payload structure
                    assert payload['solution'] == 'SO0058'
                    assert payload['data']['event']['type'] == 'tgw'
                    assert payload['data']['event']['action'] == 'network_metrics'
                    assert payload['data']['metrics']['bytes_in'] == 5000
                    assert payload['data']['metrics']['bytes_out'] == 6000

    def test_collect_all_metrics_success(self):
        """Test successful collection of all metrics"""
        mock_attachments = [
            {'TransitGatewayAttachmentId': 'tgw-attach-1', 'VpcId': 'vpc-1'},
            {'TransitGatewayAttachmentId': 'tgw-attach-2', 'VpcId': 'vpc-2'}
        ]
        
        with patch.object(self.metrics_collector, '_get_tgw_attachments', return_value=mock_attachments):
            with patch.object(self.metrics_collector, '_collect_attachment_metrics_batch') as mock_batch:
                with patch.object(self.metrics_collector, '_collect_tgw_metrics') as mock_tgw:
                    
                    result = self.metrics_collector.collect_all_metrics()
                    
                    # Verify all methods were called
                    mock_batch.assert_called_once_with(mock_attachments)
                    mock_tgw.assert_called_once()
                    
                    # Verify result
                    assert result['status'] == 'success'
                    assert 'Collected metrics for TGW' in result['message']
                    assert '2 attachments' in result['message']

    def test_collect_all_metrics_exception(self):
        """Test exception handling in collect_all_metrics"""
        with patch.object(self.metrics_collector, '_get_tgw_attachments', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                self.metrics_collector.collect_all_metrics()

    def test_collect_attachment_metrics_batch_large_batch(self):
        """Test batching logic for large number of attachments"""
        # Create 200 mock attachments (should be split into 2 batches)
        attachments = []
        for i in range(200):
            attachments.append({
                'TransitGatewayAttachmentId': f'tgw-attach-{i}',
                'VpcId': f'vpc-{i}'
            })
        
        with patch.object(self.metrics_collector, '_collect_batch_metrics') as mock_batch:
            self.metrics_collector._collect_attachment_metrics_batch(attachments)
            
           
            assert mock_batch.call_count == 2
            
          
            first_call_attachments = mock_batch.call_args_list[0][0][0]
            assert len(first_call_attachments) == 125
            
         
            second_call_attachments = mock_batch.call_args_list[1][0][0]
            assert len(second_call_attachments) == 75

    def test_hashed_ids_in_payload(self):
        """Test that resource IDs are properly hashed in payloads"""
        attachment = {
            'TransitGatewayAttachmentId': 'tgw-attach-123',
            'VpcId': 'vpc-123'
        }
        
        cloudwatch_response = {
            'MetricDataResults': [
                {'Id': 'att_0_bytes_in', 'Values': [1000]},
                {'Id': 'att_0_bytes_out', 'Values': [2000]},
                {'Id': 'att_0_drops_packets', 'Values': [10]},
                {'Id': 'att_0_drops_bytes', 'Values': [100]}
            ]
        }
        
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        
        with patch('solution.metrics_collector.handler.Metrics') as mock_metrics_class:
            mock_metrics_instance = Mock()
            mock_metrics_class.return_value = mock_metrics_instance
            
            self.metrics_collector._emit_attachment_metrics(
                attachment, cloudwatch_response, 0, start_time, end_time
            )
            
            payload = mock_metrics_instance.metrics.call_args[0][0]
            
            # Verify IDs are hashed (should be 64-character hex strings)
            assert len(payload['data']['attachment']['tgw_id_hash']) == 64
            assert len(payload['data']['attachment']['attachment_id_hash']) == 64
            
            # Verify account_id and stack_id are NOT hashed
            assert payload['account_id'] == '123456789012'
            assert 'arn:aws:cloudformation' in payload['stack_id']
