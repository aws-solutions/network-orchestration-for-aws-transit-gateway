# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from decimal import Decimal
from unittest.mock import patch, Mock
from urllib import error
import pytest
from datetime import datetime
from solution.tgw_vpc_attachment.lib.utils.metrics import (
    Metrics, 
    DecimalEncoder, 
    METRICS_TIMESTAMP_FORMAT
)


class TestDecimalEncoder:
    """Test class for DecimalEncoder"""

    def test_decimal_encoder_float(self):
        """Test DecimalEncoder with float decimal"""
        # ARRANGE
        encoder = DecimalEncoder()
        decimal_value = Decimal('10.5')
        
        # ACT
        result = encoder.default(decimal_value)
        
        # ASSERT
        assert result == 10.5
        assert isinstance(result, float)

    def test_decimal_encoder_int(self):
        """Test DecimalEncoder with integer decimal"""
        # ARRANGE
        encoder = DecimalEncoder()
        decimal_value = Decimal('10')
        
        # ACT
        result = encoder.default(decimal_value)
        
        # ASSERT
        assert result == 10
        assert isinstance(result, int)

    def test_decimal_encoder_non_decimal(self):
        """Test DecimalEncoder with non-decimal value"""
        # ARRANGE
        encoder = DecimalEncoder()
        
        # ACT & ASSERT
        with pytest.raises(TypeError):
            encoder.default("not a decimal")


class TestMetrics:
    """Test class for Metrics"""

    def test_metrics_init(self):
        """Test Metrics initialization"""
        # ACT
        metrics = Metrics()
        
        # ASSERT
        assert metrics.logger is not None

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_success(self, mock_urlopen):
        """Test successful metrics submission"""
        # ARRANGE
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        test_data = {'test_key': 'test_value'}
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result == 200
        mock_urlopen.assert_called_once()

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_http_error(self, mock_urlopen):
        """Test metrics submission with HTTP error"""
        # ARRANGE
        mock_urlopen.side_effect = error.HTTPError(
            url='test', code=400, msg='Bad Request', hdrs=None, fp=None
        )

        test_data = {'test_key': 'test_value'}
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result == 400

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_url_error(self, mock_urlopen):
        """Test metrics submission with URL error"""
        # ARRANGE
        mock_urlopen.side_effect = error.URLError('Connection failed')

        test_data = {'test_key': 'test_value'}
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result == 'Connection failed'

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_with_default_env_values(self, mock_urlopen):
        """Test metrics with default environment values"""
        # ARRANGE
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        test_data = {'test_key': 'test_value'}
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result == 200
        
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode('utf-8'))
        
        assert request_data['AccountId'] == 'unknown'
        assert request_data['StackId'] == 'unknown'
        assert request_data['UUID'] == 'test-uuid-123'
        assert request_data['Solution'] == 'SO0058'
        assert request_data['Data'] == test_data

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_with_decimal_data(self, mock_urlopen):
        """Test metrics with decimal data to cover DecimalEncoder"""
        # ARRANGE
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        test_data = {
            'decimal_float': Decimal('10.5'),
            'decimal_int': Decimal('20'),
            'regular_value': 'test'
        }
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result == 200
        
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode('utf-8'))
        
        assert request_data['Data']['decimal_float'] == 10.5
        assert request_data['Data']['decimal_int'] == 20
        assert request_data['Data']['regular_value'] == 'test'

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_with_custom_solution_and_url(self, mock_urlopen):
        """Test metrics with custom solution ID and URL"""
        # ARRANGE
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        test_data = {'test_key': 'test_value'}
        custom_solution_id = 'CUSTOM123'
        custom_url = 'https://custom.metrics.endpoint.com/api'
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data, custom_solution_id, custom_url)
        
        # ASSERT
        assert result == 200
        
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode('utf-8'))
        
        assert request_data['Solution'] == custom_solution_id
        assert request_obj.full_url == custom_url

    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.json.dumps')
    def test_metrics_general_exception(self, mock_json_dumps):
        """Test metrics with general exception"""
        # ARRANGE
        mock_json_dumps.side_effect = Exception('JSON serialization error')

        test_data = {'test_key': 'test_value'}
        metrics = Metrics()
        
        # ACT
        result = metrics.metrics(test_data)
        
        # ASSERT
        assert result is None

    @patch.dict(os.environ, {
        'SOLUTION_UUID': 'test-uuid-123',
        'AWS_ACCOUNT_ID': '123456789012',
        'STACK_ID': 'test-stack-id'
    })
    @patch('solution.tgw_vpc_attachment.lib.utils.metrics.request.urlopen')
    def test_metrics_timestamp_format(self, mock_urlopen):
        """Test metrics timestamp formatting"""
        # ARRANGE
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        test_data = {'test_key': 'test_value'}
        metrics = Metrics()

        # ACT
        result = metrics.metrics(test_data)

        # ASSERT
        assert result == 200
        
        # Verify the timestamp format
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode('utf-8'))
        timestamp = request_data['TimeStamp']
        
        try:
            datetime.strptime(timestamp, METRICS_TIMESTAMP_FORMAT)
            is_valid_format = True
        except ValueError:
            is_valid_format = False
        
        assert is_valid_format, (
            f"Timestamp {timestamp} does not match expected format '{METRICS_TIMESTAMP_FORMAT}'"
        )
