#!/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import boto3
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from aws_lambda_powertools import Logger

from solution.tgw_vpc_attachment.lib.utils.metrics import Metrics
from solution.tgw_vpc_attachment.lib.clients.boto3_config import boto3_config


AWS_TRANSIT_GATEWAY_NAMESPACE = 'AWS/TransitGateway'
METRICS_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

ec2_client = boto3.client('ec2', config=boto3_config)
cloudwatch_client = boto3.client('cloudwatch', config=boto3_config)

class MetricsCollector:
    
    def __init__(self, event: Dict[str, Any], logger: Logger) -> None:
        self.event = event
        self.logger = logger
        self.ec2_client = ec2_client
        self.cloudwatch_client = cloudwatch_client
        
        # Get the single TGW managed by this solution
        self.tgw_id: str = self._get_solution_tgw_id()
        self.logger.info(f"Initialized with TGW: {self.tgw_id}")
        
        # Calculate previous day start and end times once
        previous_day = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        self.start_time: datetime = datetime.combine(previous_day, datetime.min.time()).replace(tzinfo=timezone.utc)
        self.end_time: datetime = datetime.combine(previous_day, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        self.solution_uuid: Optional[str] = os.environ.get('SOLUTION_UUID')
        
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all network metrics for TGW and attachments"""
        try:
            self.logger.info(f"Starting network metrics collection for TGW: {self.tgw_id}")
            
          
            attachments: List[Dict[str, Any]] = self._get_tgw_attachments(self.tgw_id)
            self.logger.info(f"Found {len(attachments)} attachments to collect metrics for")
            
           
            self._collect_attachment_metrics_batch(attachments)
            
         
            self._collect_tgw_metrics()
            
            return {
                "status": "success", 
                "message": f"Collected metrics for TGW {self.tgw_id} with {len(attachments)} attachments",
                "solution_uuid": self.solution_uuid
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {str(e)}")
            raise

    def _get_solution_tgw_id(self) -> str:
        """Get the single TGW ID managed by STNO solution"""
        tgw_id = os.environ.get('TGW_ID')
        if not tgw_id:
            raise ValueError("TGW_ID environment variable not set")
        return tgw_id

    def _get_tgw_attachments(self, tgw_id: str) -> List[Dict[str, Any]]:
        """Get all solution-managed attachments for the TGW"""
        all_attachments: List[Dict[str, Any]] = []
        next_token: Optional[str] = None
        
        while True:
            params: Dict[str, Any] = {
                'Filters': [
                    {
                        'Name': 'transit-gateway-id',
                        'Values': [tgw_id]
                    },
                    {
                        'Name': 'state',
                        'Values': ['available']
                    },
                ]
            }
            
            if next_token:
                params['NextToken'] = next_token
            
            response = self.ec2_client.describe_transit_gateway_vpc_attachments(**params)
            all_attachments.extend(response['TransitGatewayVpcAttachments'])
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        return all_attachments

    def _collect_attachment_metrics_batch(self, attachments: List[Dict[str, Any]]) -> None:
        """Collect metrics for attachments in batches to handle CloudWatch 500 query limit"""
        batch_size: int = 125
        
        for i in range(0, len(attachments), batch_size):
            batch: List[Dict[str, Any]] = attachments[i:i + batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} attachments")
            self._collect_batch_metrics(batch)

    def _collect_batch_metrics(self, attachments: List[Dict[str, Any]]) -> None:
        """Collect metrics for a batch of attachments using single CloudWatch call"""        
        metric_queries: List[Dict[str, Any]] = []
        for attachment in attachments:
            attachment_id: str = attachment['TransitGatewayAttachmentId']
            sanitized_id: str = attachment_id.replace('-', '_')
            
            metric_queries.extend([
                {
                    'Id': f'{sanitized_id}_bytes_in',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'BytesIn',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id},
                                {'Name': 'TransitGatewayAttachment', 'Value': attachment_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': f'{sanitized_id}_bytes_out',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'BytesOut',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id},
                                {'Name': 'TransitGatewayAttachment', 'Value': attachment_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': f'{sanitized_id}_drops_packets',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'PacketDropCountBlackhole',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id},
                                {'Name': 'TransitGatewayAttachment', 'Value': attachment_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': f'{sanitized_id}_drops_bytes',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'ByteDropCountBlackhole',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id},
                                {'Name': 'TransitGatewayAttachment', 'Value': attachment_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                }
            ])
        

        all_metric_results: List[Dict[str, Any]] = []
        next_token: Optional[str] = None
        
        while True:
            params: Dict[str, Any] = {
                'MetricDataQueries': metric_queries,
                'StartTime': self.start_time,
                'EndTime': self.end_time
            }
            if next_token:
                params['NextToken'] = next_token
            
            response = self.cloudwatch_client.get_metric_data(**params)
            all_metric_results.extend(response['MetricDataResults'])
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        metrics_map: Dict[str, Dict[str, Any]] = {result['Id']: result for result in all_metric_results}
        
        for attachment in attachments:
            attachment_id: str = attachment['TransitGatewayAttachmentId']
            sanitized_id: str = attachment_id.replace('-', '_')
            
            attachment_metrics: Dict[str, Dict[str, Any]] = {
                'bytes_in': metrics_map.get(f'{sanitized_id}_bytes_in', {}),
                'bytes_out': metrics_map.get(f'{sanitized_id}_bytes_out', {}),
                'drops_packets': metrics_map.get(f'{sanitized_id}_drops_packets', {}),
                'drops_bytes': metrics_map.get(f'{sanitized_id}_drops_bytes', {})
            }
            
            self._emit_attachment_metrics(attachment, attachment_metrics)

    def _emit_attachment_metrics(self, attachment: Dict[str, Any], attachment_metrics: Dict[str, Dict[str, Any]]) -> None:
        """Emit metrics for a single attachment"""
        attachment_id: str = attachment['TransitGatewayAttachmentId']
        bytes_in: float = attachment_metrics['bytes_in'].get('Values', [0])[0] if attachment_metrics['bytes_in'].get('Values') else 0
        bytes_out: float = attachment_metrics['bytes_out'].get('Values', [0])[0] if attachment_metrics['bytes_out'].get('Values') else 0
        drops_packets: float = attachment_metrics['drops_packets'].get('Values', [0])[0] if attachment_metrics['drops_packets'].get('Values') else 0
        drops_bytes: float = attachment_metrics['drops_bytes'].get('Values', [0])[0] if attachment_metrics['drops_bytes'].get('Values') else 0
        
        attachment_created_at = attachment.get('CreationTime')
        if attachment_created_at:
            attachment_created_at = attachment_created_at.strftime(METRICS_TIMESTAMP_FORMAT)
       
        payload: Dict[str, Any] = {
            "uuid": self.solution_uuid,
            "timestamp": datetime.now(timezone.utc).strftime(METRICS_TIMESTAMP_FORMAT),
            "solution": "SO0058",
            "account_id": os.environ.get('AWS_ACCOUNT_ID', ''),
            "stack_id": os.environ.get('STACK_ID', ''),
            "region": os.environ.get('AWS_REGION', ''),
            "data": {
                "event": {
                    "type": "tgw_attachment",
                    "action": "network_metrics"
                },
                "attachment": {
                    "tgw_id_hash": hashlib.sha256(self.tgw_id.encode()).hexdigest(),
                    "attachment_id_hash": hashlib.sha256(attachment_id.encode()).hexdigest(),
                    "created_at": attachment_created_at
                },
                "metrics": {
                    "bytes_in": int(bytes_in),
                    "bytes_out": int(bytes_out),
                    "drops_packets": int(drops_packets),
                    "drops_bytes": int(drops_bytes),
                    "window_start": self.start_time.strftime(METRICS_TIMESTAMP_FORMAT),
                    "window_end": self.end_time.strftime(METRICS_TIMESTAMP_FORMAT)
                }
            }
        }
        
        Metrics().metrics(payload)
        self.logger.debug(f"Emitted metrics for attachment {attachment_id}")

    def _collect_tgw_metrics(self) -> None:
        """Collect TGW-level network metrics"""
        tgw_info = self.ec2_client.describe_transit_gateways(TransitGatewayIds=[self.tgw_id])
        tgw_created_at: Optional[str] = None
        if tgw_info['TransitGateways']:
            tgw_created_at = tgw_info['TransitGateways'][0]['CreationTime'].strftime(METRICS_TIMESTAMP_FORMAT)
        
        # Get TGW-level metrics
        response = self.cloudwatch_client.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'tgw_bytes_in',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'BytesIn',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'tgw_bytes_out',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'BytesOut',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'tgw_drops_packets',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'PacketDropCountBlackhole',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'tgw_drops_bytes',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': AWS_TRANSIT_GATEWAY_NAMESPACE,
                            'MetricName': 'ByteDropCountBlackhole',
                            'Dimensions': [
                                {'Name': 'TransitGateway', 'Value': self.tgw_id}
                            ]
                        },
                        'Period': 86400,
                        'Stat': 'Sum'
                    }
                }
            ],
            StartTime=self.start_time,
            EndTime=self.end_time
        )
        
        # Extract metrics
        metrics_map: Dict[str, Dict[str, Any]] = {result['Id']: result for result in response['MetricDataResults']}
        
        bytes_in: float = metrics_map.get('tgw_bytes_in', {}).get('Values', [0])[0] if metrics_map.get('tgw_bytes_in', {}).get('Values') else 0
        bytes_out: float = metrics_map.get('tgw_bytes_out', {}).get('Values', [0])[0] if metrics_map.get('tgw_bytes_out', {}).get('Values') else 0
        drops_packets: float = metrics_map.get('tgw_drops_packets', {}).get('Values', [0])[0] if metrics_map.get('tgw_drops_packets', {}).get('Values') else 0
        drops_bytes: float = metrics_map.get('tgw_drops_bytes', {}).get('Values', [0])[0] if metrics_map.get('tgw_drops_bytes', {}).get('Values') else 0
        
        # Create TGW payload
        payload: Dict[str, Any] = {
            "uuid": self.solution_uuid,
            "timestamp": datetime.now(timezone.utc).strftime(METRICS_TIMESTAMP_FORMAT),
            "solution": "SO0058",
            "account_id": os.environ.get('AWS_ACCOUNT_ID', ''),
            "stack_id": os.environ.get('STACK_ID', ''),
            "region": os.environ.get('AWS_REGION', ''),
            "data": {
                "event": {
                    "type": "tgw",
                    "action": "network_metrics"
                },
                "tgw": {
                    "tgw_id_hash": hashlib.sha256(self.tgw_id.encode()).hexdigest(),
                    "created_at": tgw_created_at
                },
                "metrics": {
                    "bytes_in": int(bytes_in),
                    "bytes_out": int(bytes_out),
                    "drops_packets": int(drops_packets),
                    "drops_bytes": int(drops_bytes),
                    "window_start": self.start_time.strftime(METRICS_TIMESTAMP_FORMAT),
                    "window_end": self.end_time.strftime(METRICS_TIMESTAMP_FORMAT)
                }
            }
        }
        
       
        Metrics().metrics(payload)
        self.logger.info(f"Emitted TGW-level metrics for {self.tgw_id}")
