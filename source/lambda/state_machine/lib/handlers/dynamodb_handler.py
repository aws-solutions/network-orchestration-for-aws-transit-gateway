# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
import os
from datetime import datetime, timedelta
from os import environ

from aws_lambda_powertools import Logger

from state_machine.lib.clients.dynamodb import DDB
from state_machine.lib.handlers.general_functions_handler import GeneralFunctions
from state_machine.lib.utils.helper import current_time

EXECUTING = "Executing: "


class DynamoDb:

    def __init__(self, event):
        self.event = event
        self.logger = Logger(os.getenv('LOG_LEVEL'))
        self.logger.info(event)

    def _get_time_to_live(self, time) -> str:
        utc_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        orig = datetime.fromtimestamp(int(epoch_time))
        ttl = orig + timedelta(days=int(environ.get("TTL")))
        return str(int((ttl - datetime(1970, 1, 1)).total_seconds()))

    def put_item(self):
        try:
            self.logger.info(
                EXECUTING
                + self.__class__.__name__
                + "/"
                + inspect.stack()[0][3]
            )
            ddb = DDB(environ.get("TABLE_NAME"))

            # The SubnetId is the hash key for the table, and is used by the UI to get the latest event.
            # If there is a association/propagation tag change on an existing VPC already added to the TGW,
            # then the SubnetId will be empty (None), and thus the UI will show an entry for the latest
            # event with the SubnetId None set to the most recent VPC change, which will be overwritten with
            # newer VPC events. To prevent this, we try to populate the SubnetId with something, like the VpcId:
            if not self.event.get("SubnetId"):
                vpc_id = self.event.get("VpcId")
                if vpc_id:
                    self.event.update({"SubnetId": vpc_id})

            item = {
                "SubnetId": self.event.get("SubnetId", "None"),
                "Version": str(self.event.get("detail", {}).get("version", "None")),
                "AvailabilityZone": self.event.get("AvailabilityZone", "None"),
                "VpcId": self.event.get("VpcId", "None"),
                "VpcName": self.event.get("VpcName", "None"),
                "TgwId": environ.get("TGW_ID", "None"),
                "PropagationRouteTables": self.event.get(environ.get("PROPAGATION_TAG")),
                "PropagationRouteTablesString":
                    "None" if self.event.get(environ.get("PROPAGATION_TAG")) is None
                    else ",".join(self.event.get(environ.get("PROPAGATION_TAG"))),
                "TagEventSource": self.event.get("TagEventSource", "None"),
                "VpcCidr": self.event.get("VpcCidr", "None"),
                "Action": self.event.get("Action", "None"),
                "Status": self.event.get("Status", "None"),
                "AWSSpokeAccountId": self.event.get("account", "None"),
                "UserId":
                    "StateMachine" if self.event.get("UserId") is None
                    else self.event.get("UserId"),
                "AssociationRouteTable": self.event.get(environ.get("ASSOCIATION_TAG")),
                "RequestTimeStamp": self.event.get("time"),
                "ResponseTimeStamp":
                    current_time() if self.event.get("GraphQLTimeStamp") is None
                    else self.event.get("GraphQLTimeStamp"),
                "TimeToLive": self._get_time_to_live(self.event.get("time")),
                "Comment": self.event.get("Comment", "None"),
            }

            self.logger.info(item)
            # add item to the DDB table with version in event
            ddb.put_item(item)

            item.update({"Version": "latest"})
            ddb.put_item(item)

            GeneralFunctions(self.event).send_anonymous_data()

            return self.event
        except Exception as e:
            message = {
                "FILE": __file__.split("/")[-1],
                "CLASS": self.__class__.__name__,
                "METHOD": inspect.stack()[0][3],
                "EXCEPTION": str(e),
            }
            self.logger.exception(message)
            raise
