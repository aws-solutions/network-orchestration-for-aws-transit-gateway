#!/bin/python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import os
import boto3
import botocore
from aws_lambda_powertools import Logger

from solution.metrics_collector.handler import MetricsCollector

logger = Logger(level=os.getenv('LOG_LEVEL'), service="METRICS_COLLECTOR")
logger.debug("boto3 version:" + boto3.__version__)
logger.debug("botocore version:" + botocore.__version__)


def lambda_handler(event, _context):
    """
    Handles scheduled metrics collection for TGW network health
    """
    try:
        logger.info("Metrics Collector - Starting scheduled metrics collection")
        logger.info(f"Event: {event}")
        
        metrics = MetricsCollector(event, logger)
        response = metrics.collect_all_metrics()
        
        logger.info(f"Metrics collection completed: {response}")
        return response
            
    except Exception as error:
        logger.exception("Error while executing metrics collector lambda handler")
        raise error
