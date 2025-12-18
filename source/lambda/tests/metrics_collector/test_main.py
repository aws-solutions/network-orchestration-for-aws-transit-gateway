#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for metrics collector main Lambda handler"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from solution.metrics_collector.main import lambda_handler


class TestMetricsCollectorMain:
    """Test cases for metrics collector main Lambda handler"""

    def test_lambda_handler_success(self):
        """Test successful Lambda handler execution"""
       
        test_event = {"source": "aws.events", "detail-type": "Scheduled Event"}
        test_context = Mock()
        test_context.aws_request_id = "test-request-id"
        
        # Mock MetricsCollector
        with patch('solution.metrics_collector.main.MetricsCollector') as mock_collector_class:
            mock_collector_instance = Mock()
            mock_collector_instance.collect_all_metrics.return_value = {
                "status": "success",
                "message": "Collected metrics for TGW tgw-123 with 5 attachments",
                "run_uuid": "test-uuid"
            }
            mock_collector_class.return_value = mock_collector_instance
            
          
            result = lambda_handler(test_event, test_context)
            
           
            mock_collector_class.assert_called_once()
            call_args = mock_collector_class.call_args[0]
            assert call_args[0] == test_event  
           
            assert call_args[1] is not None  
            
        
            mock_collector_instance.collect_all_metrics.assert_called_once()
            
   
            assert result["status"] == "success"
            assert "Collected metrics for TGW" in result["message"]

    def test_lambda_handler_exception(self):
        """Test Lambda handler exception handling"""
        test_event = {"source": "aws.events"}
        test_context = Mock()
        
        # Mock MetricsCollector to raise exception
        with patch('solution.metrics_collector.main.MetricsCollector') as mock_collector_class:
            mock_collector_instance = Mock()
            mock_collector_instance.collect_all_metrics.side_effect = Exception("Test error")
            mock_collector_class.return_value = mock_collector_instance
            
            # Execute handler and expect exception
            with pytest.raises(Exception, match="Test error"):
                lambda_handler(test_event, test_context)

    def test_lambda_handler_logging(self):
        """Test that Lambda handler logs appropriately"""
        test_event = {"source": "aws.events"}
        test_context = Mock()
        
        with patch('solution.metrics_collector.main.MetricsCollector') as mock_collector_class:
            with patch('solution.metrics_collector.main.logger') as mock_logger:
                mock_collector_instance = Mock()
                mock_collector_instance.collect_all_metrics.return_value = {"status": "success"}
                mock_collector_class.return_value = mock_collector_instance
                
                lambda_handler(test_event, test_context)
                
              
                mock_logger.info.assert_any_call("Metrics Collector - Starting scheduled metrics collection")
                mock_logger.info.assert_any_call(f"Event: {test_event}")
                mock_logger.info.assert_any_call(f"Metrics collection completed: {{'status': 'success'}}")

    def test_lambda_handler_different_event_types(self):
        """Test Lambda handler with different event types"""
        
        eventbridge_event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {"action": "collect_all_metrics"}
        }
        
        test_context = Mock()
        
        with patch('solution.metrics_collector.main.MetricsCollector') as mock_collector_class:
            mock_collector_instance = Mock()
            mock_collector_instance.collect_all_metrics.return_value = {"status": "success"}
            mock_collector_class.return_value = mock_collector_instance
            
            result = lambda_handler(eventbridge_event, test_context)
            
           
            assert result["status"] == "success"
            mock_collector_instance.collect_all_metrics.assert_called_once()

    def test_lambda_handler_with_logger_configuration(self):
        """Test that logger is properly configured"""
      
        from solution.metrics_collector.main import logger
        
 
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
