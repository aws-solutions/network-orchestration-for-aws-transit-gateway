# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from os import environ, getenv

from aws_lambda_powertools import Logger
from mypy_boto3_ec2.type_defs import TransitGatewayRouteTableTypeDef


class ApprovalTagHandler:
    def __init__(self, event):
        self.event = event
        self.logger = Logger(level=getenv('LOG_LEVEL'), service=self.__class__.__name__)
        self.route_table_approval_required = {}
        self.association_route_table_id = self.event.get("AssociationRouteTableId")
        self.propagation_route_table_ids = self.event.get("PropagationRouteTableIds", [])
        self.route_table_rule_tags = {}
        self.rule = {}

    def analyze(self, tgw_route_tables: list[TransitGatewayRouteTableTypeDef]):

        # set approval required to 'No', assuming if tag is not present it does not require approval
        self.event.update({"ApprovalRequired": "no"})

        if not self.association_route_table_id or self.association_route_table_id == "none":
            # No association tag, propagations are irrelevant. Skip:
            return self.event

        self.get_and_set_route_table_tags(tgw_route_tables)

        self.read_rule_association_route_table()

        self.read_rule_propagation_route_table()

        self.set_approval_tags_for_association()

        self.set_approval_tags_for_propagations()

        return self.event

    def get_and_set_route_table_tags(self, tgw_route_tables: list[TransitGatewayRouteTableTypeDef]):
        for route_table in tgw_route_tables:
            self.logger.debug(f"PROCESSING_ROUTE_TABLE: {route_table}")
            route_table_id = route_table.get("TransitGatewayRouteTableId")
            if route_table_id == self.association_route_table_id or route_table_id in self.propagation_route_table_ids:
                # Collect ApprovalRule-* tag keys and values if any:

                self.route_table_approval_required[route_table_id] = {
                    "association_approval": False,
                    "propagation_approval": False,
                }
                self.set_approval_tags_for_tgw_route_table(route_table_id, route_table)

                # If the approval is conditional, construct the rule object to insert into
                # route_table_approval_required:
                if self.route_table_approval_required.get(route_table_id, {}).get("conditional_approval"):
                    # Convert rule tags into a rule object
                    self.logger.debug(f"ROUTE_TABLE_RULE_TAGS (GET_SET): {self.route_table_rule_tags}")
                    self.logger.debug(f"ROUTE_TABLE_RULE (Before): {self.rule}")
                    self.rule["default_association"] = self.rule["default_propagation"] = "ApprovalRequired"
                    if "ApprovalRule-Default-Association".lower() in self.route_table_rule_tags:
                        self.rule["default_association"] = self.route_table_rule_tags[
                            "ApprovalRule-Default-Association".lower()]
                    if "ApprovalRule-Default-Propagation".lower() in self.route_table_rule_tags:
                        self.rule["default_propagation"] = self.route_table_rule_tags[
                            "ApprovalRule-Default-Propagation".lower()]
                    self.get_numbered_approval_tags()

                    # Insert final rule object for this route table ID:
                    self.route_table_approval_required[route_table_id]["rule"] = self.rule

        self.logger.debug(f"ROUTE_TABLE_RULE (After): {self.rule}")

    def get_numbered_approval_tags(self):
        # Get all the Approval-NN-* tags in a group, from 00 to 99 if it exists:
        for i in range(1, 100):
            zero_padded_number = str(i).zfill(2)
            # Get all rules, if any, that starts with this number:
            rule_group_tags = {
                key: value
                for key, value in self.route_table_rule_tags.items()
                if key.startswith(f"ApprovalRule-{zero_padded_number}-".lower())
            }
            self.logger.debug(f"RULE_GROUP_TAGS: {rule_group_tags}")
            if len(rule_group_tags) == 0:
                break
            # Create rule block for the number i
            rule_number_block = {}

            def csv_to_list(csv):
                return [value.strip() for value in filter(None, csv.split(","))]

            tag_key = f"ApprovalRule-{zero_padded_number}-InOUs".lower()
            if rule_group_tags.get(tag_key):
                ou_list = csv_to_list(rule_group_tags.get(tag_key))
                rule_number_block["InOUs"] = ou_list

            tag_key = f"ApprovalRule-{zero_padded_number}-NotInOUs".lower()
            if rule_group_tags.get(tag_key):
                ou_list = csv_to_list(rule_group_tags.get(tag_key))
                rule_number_block["NotInOUs"] = ou_list

            tag_key = f"ApprovalRule-{zero_padded_number}-Association".lower()
            if rule_group_tags.get(tag_key):
                rule_number_block["Association"] = rule_group_tags.get(tag_key)

            tag_key = f"ApprovalRule-{zero_padded_number}-Propagation".lower()
            if rule_group_tags.get(tag_key):
                rule_number_block["Propagation"] = rule_group_tags.get(tag_key)

            # Set the rule number:
            self.rule[i] = rule_number_block

    def set_approval_tags_for_tgw_route_table(self, route_table_id, table: TransitGatewayRouteTableTypeDef):
        # iterate through tags for each route table
        for tag in table.get("Tags"):
            self.logger.debug(f"PROCESSING_TAG: {tag}")
            approval_key = environ.get("APPROVAL_KEY").lower().strip()
            tag_key = tag.get("Key").lower().strip()
            tag_value = tag.get("Value").lower().strip()
            self.logger.debug(f"TAG_KEY: {tag_key}")
            self.logger.debug(f"TAG_VALUE: {tag_value}")

            if tag_key == approval_key:
                self.logger.info(f"Found approval tag key {approval_key} set to '{tag_value}')")
                if tag_value == "yes":
                    # if approval required for this route table change
                    self.logger.info("Any change to this route domain require approval.")
                    self.route_table_approval_required[route_table_id] = {
                        "association_approval": True,
                        "propagation_approval": True,
                    }
                elif tag_value == "conditional":
                    self.route_table_approval_required[route_table_id] = {
                        "conditional_approval": True,
                    }
            elif tag_key.startswith("ApprovalRule".lower()):
                # Collect the rules for this route table:
                self.logger.debug("FOUND_APPROVAL_RULE")
                self.route_table_rule_tags[tag_key] = tag_value
                self.logger.debug(f"Adding Key:Value to ROUTE_TABLE_RULE_TAGS: {self.route_table_rule_tags}")

    def set_approval_tags_for_propagations(self):
        # set approval on propagation changes
        # iterate through the route table ids with enabled propagations routes tables
        # in the tagging event in the propagate-to key
        for route_table in self.propagation_route_table_ids:
            # check if this route table change requires approval
            self.logger.debug(f"PROPAGATION_APPROVAL {self.route_table_approval_required[route_table].get('propagation_approval')}")
            if self.route_table_approval_required[route_table].get("propagation_approval"):
                self.logger.info(f"Found approval required tag on: {route_table}")
                if self.event.get("ExistingPropagationRouteTableIds") is not None \
                        and route_table in self.event.get("ExistingPropagationRouteTableIds"):
                    self.logger.info(
                        f"Route table: {route_table} is in the existing propagation list,"
                        f" NO approval required.")
                else:
                    self.logger.info(
                        f"Route table: {route_table} is not in the existing propagation list. "
                        f"Requires Approval.")
                    self.event.update({"ApprovalRequired": "yes"})
                    self.event.update({"PropagationNeedsApproval": "yes"})
            else:
                self.logger.info(f"Approval not required for Route Table: {route_table}")

    def set_approval_tags_for_association(self):
        # set approval on association changes
        if self.route_table_approval_required[self.association_route_table_id].get("association_approval"):
            # condition to check if already existing associated VPC settings are being changed.
            # example: change in propagation, add or remove subnet.
            if self.association_route_table_id == self.event.get(
                    "ExistingAssociationRouteTableId"
            ):
                self.logger.info(
                    "Updating other setting for an existing association, no approval required."
                )
            else:
                self.logger.info(
                    "Found association route table that requires approval"
                )
                self.event.update({"ApprovalRequired": "yes"})
                self.event.update({"AssociationNeedsApproval": "yes"})

    def read_rule_propagation_route_table(self):
        for propagation_route_table in self.propagation_route_table_ids:
            if self.route_table_approval_required[propagation_route_table].get("conditional_approval"):
                self.rule = self.route_table_approval_required[propagation_route_table].get("rule")
                if self.rule:
                    # action will be one of "accept|reject|approvalrequired"
                    action = self._process_conditional_approval_rule("Propagation").lower()
                    self.logger.debug(f"ACTION: {action}")
                    self.logger.info(
                        f'Conditional rule result is {action} for propagation route table '
                        f'{propagation_route_table}'
                    )
                    if action == "accept":
                        self.route_table_approval_required[propagation_route_table]["propagation_approval"] = False
                    elif action == "ApprovalRequired".lower():
                        self.route_table_approval_required[propagation_route_table]["propagation_approval"] = True
                    elif action == "reject":
                        self.event.update({"ConditionalApproval": "auto-rejected"})
                        self.route_table_approval_required[propagation_route_table]["propagation_approval"] = True

    def read_rule_association_route_table(self):
        # If the ApprovalRequired is conditional, we need to process the rules and then
        # for the route_table_approval_required dictionary,
        # set the tgw-rtb-id -> association_approval|propagation_approval to True/False
        # for the next section:
        if self.route_table_approval_required[self.association_route_table_id].get("conditional_approval"):
            self.rule = self.route_table_approval_required[self.association_route_table_id].get("rule")
            if self.rule:
                # action will be one of "accept|reject|approvalrequired"
                action = self._process_conditional_approval_rule("Association").lower()
                self.logger.debug(f"ACTION: {action}")
                self.logger.info(
                    f'Conditional rule result is {action} for association '
                    f'route table {self.association_route_table_id}'
                )
                if action == "accept":
                    self.logger.debug("ACTION set to Accept")
                    self.route_table_approval_required[self.association_route_table_id]["association_approval"] = False
                elif action == "ApprovalRequired".lower():
                    self.logger.debug("ACTION set to ApprovalRequired")
                    self.route_table_approval_required[self.association_route_table_id]["association_approval"] = True
                elif action == "reject":
                    self.logger.debug("ACTION set to Reject")
                    self.event.update({"ConditionalApproval": "auto-rejected"})
                    self.route_table_approval_required[self.association_route_table_id]["association_approval"] = True
                self.logger.info(f"ROUTE_TABLE_APPROVAL_REQUIRED: {self.route_table_approval_required}")
                self.logger.info(f"ASSOCIATION_RULE: {self.rule}")

    def _process_conditional_approval_rule(self, route_type):
        # Default action if nothing matches:
        default_action = "ApprovalRequired".lower()
        self.logger.debug(f"ROUTE_TYPE: {route_type}")
        action = self.rule.get(f"default_{route_type.lower()}", default_action)

        # Get current event account's OU:
        account_in_ou = self.event.get("AccountOuPath")
        if not account_in_ou:
            self.logger.info("Cannot get account OU path from event.")
            return action

        # Do a case-insensitive match:
        account_in_ou = account_in_ou.lower()
        self.logger.debug(f"Account in OU: {account_in_ou}")
        self.logger.debug(f"RULE_KEYS: {self.rule}")
        rule_ids = sorted([x for x in self.rule.keys() if type(x) == int])
        self.logger.debug(f"RULE_IDS: {rule_ids}")
        # Go through each number:
        for rule_id in rule_ids:
            ou_list, in_ou_rule = self.get_ou_list(rule_id)
            # Go through each OU in the list:
            for ou_path_in_tag in ou_list:
                ou_path_in_tag = self.denormalize_ou_path(ou_path_in_tag)
                self.logger.debug(f"Checking OU Path in tag: {ou_path_in_tag}")
                if in_ou_rule and account_in_ou.startswith(ou_path_in_tag):
                    action = self.rule[rule_id].get(route_type, default_action)
                    self.logger.debug(f"InOU Rule found and OU Path {account_in_ou} starts with: {ou_path_in_tag}, "
                                      f"route path: {route_type}; ®action: {action}")
                    return action
                if not in_ou_rule and not account_in_ou.startswith(ou_path_in_tag):
                    action = self.rule[rule_id].get(route_type, default_action)
                    self.logger.debug(f"NotInOU Rule found and OU Path {account_in_ou} DOES NOT start with:"
                                      f" {ou_path_in_tag}, route path: {route_type}; action: {action}")
                    return action
        return action

    def denormalize_ou_path(self, ou_path):
        self.logger.debug(f"PRINT_OU_PATH: {ou_path}")
        # Complete the OU path if user put in "Sandbox" for the OU instead of "Root/Sandbox/":
        if not ou_path.startswith("root/"):
            ou_path = f"root/{ou_path}"
        if not ou_path.endswith("/"):
            ou_path = f"{ou_path}/"
        return ou_path

    def get_ou_list(self, rule_id):
        ou_list = []
        is__in_ou__rule = True

        if "InOUs" in self.rule[rule_id]:
            ou_list = self.rule[rule_id]["InOUs"]
        elif "NotInOUs" in self.rule[rule_id]:
            is__in_ou__rule = False
            ou_list = self.rule[rule_id]["NotInOUs"]
        self.logger.debug(f"OU_LIST: {ou_list}; Found OU In Rule Flag: {is__in_ou__rule}")
        return ou_list, is__in_ou__rule
