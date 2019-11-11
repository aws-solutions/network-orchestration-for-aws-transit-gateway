######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# !/bin/python

from lib.metrics import Metrics
from lib.ec2 import EC2
from lib.dynamodb import DDB
from lib.ram import RAM
from lib.sts import STS
from lib.sns import SNS
from lib.helper import timestamp_message, current_time
from lib.assume_role_helper import AssumeRole
from os import environ
import inspect
from time import sleep
from datetime import datetime, timedelta
from random import randint


class TransitGateway(object):
    """
    This class contains functions to manage Transit Gateway related resources.
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.spoke_account_id = self.event.get('account')
        self.spoke_region = self.event.get('region')
        self.assume_role = AssumeRole()
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return EC2(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def _print(self, description, response):
        self.logger.info('Printing {}'.format(description))
        self.logger.info(response)

    def _message(self, method, e):
        return {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                'METHOD': method, 'EXCEPTION': str(e)}

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)
            ec2.create_tags(resource, 'STNOStatus-' + key, timestamp_message(message))
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def get_transit_gateway_vpc_attachment_state(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # skip checking the TGW attachment status if it does not exist
            if self.event.get('TgwAttachmentExist').lower() == 'yes':
                ec2 = self._session(self.spoke_region, self.spoke_account_id)
                response = ec2.get_transit_gateway_vpc_attachment_state(self.event.get('TransitGatewayAttachmentId'))
                self._print('Transit Gateway Attachment State: ', response)
                # the list should always contain a single item
                self.event.update({'AttachmentState': response[0].get('State')})
                if response[0].get('State') == 'pending' or response[0].get('State') == 'modifying':
                    # if the tgw attachment stage is modifying and multiple state machine executions are in progress
                    # sleeping for random number of seconds to avoid race condition failure.
                    _seconds = randint(5, 10)
                    sleep(_seconds)
            else:
                # set attachment state to deleted because it does not exist
                # and creation was skipped in the CRUD operation stage.
                # The attachment was previously deleted or was never created.
                self.logger.info("TGW Attachment does not exist.")
                self.event.update({'AttachmentState': 'deleted'})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def describe_transit_gateway_vpc_attachments(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)
            states = ['available', 'pending', 'modifying']
            response = ec2.describe_transit_gateway_vpc_attachments(environ.get('TGW_ID'),
                                                                    self.event.get('VpcId'),
                                                                    states)
            self._print('Transit Gateway Attachment List', response)

            if response:
                self.event.update({'TgwAttachmentExist': 'yes'})

                # check if the subnet is already in the TGW VPC Attachment
                for attachment in response:
                    if attachment.get('VpcId') == self.event.get('VpcId'):
                        # add TGW Attachment Id in the event for modifications in the state machine
                        self.event.update({'TransitGatewayAttachmentId': attachment.get('TransitGatewayAttachmentId')})
                        self.event.update({'AttachmentState': attachment.get('State')})
                        # look for subnet id in existing attachment
                        if self.event.get('SubnetId') in attachment.get('SubnetIds'):
                            self._print('subnet found in existing attachment', self.event.get('SubnetId'))
                            self.event.update({'FoundExistingSubnetInAttachment': 'yes'})
                        else:
                            self._print('subnet list for existing TGW-VPC attachment', attachment.get('SubnetIds'))
                            self.event.update({'FoundExistingSubnetInAttachment': 'no'})
            else:
                self.event.update({'TgwAttachmentExist': 'no'})
                self.event.update({'AttachmentState': 'does-not-exist'})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _create_tgw_attachment(self, ec2):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info("Creating TGW Attachment with Subnet ID: {}".format(self.event.get('SubnetId')))
            response = ec2.create_transit_gateway_vpc_attachment(environ.get('TGW_ID'),
                                                                 self.event.get('VpcId'),
                                                                 self.event.get('SubnetId'))
            self._print('Create Transit Gateway Attachment Response', response)
            self.event.update({'AttachmentState': response.get('TransitGatewayVpcAttachment', {}).get('State')})
            self.event.update({'TransitGatewayAttachmentId': response.get('TransitGatewayVpcAttachment', {}).get(
                'TransitGatewayAttachmentId')})
            self.event.update({'Action': 'CreateTgwVpcAttachment'})
            self.event.update({'TgwAttachmentExist': 'yes'})
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('SubnetId'), 'Subnet-Error', e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def _delete_tgw_attachment(self, ec2):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # if this exception is thrown then it is safe to delete transit gateway attachment
            delete_response = ec2.delete_transit_gateway_vpc_attachment(self.event.get('TransitGatewayAttachmentId'))
            self._print('Delete Transit Gateway Attachment Response', delete_response)
            self.event.update({'AttachmentState': delete_response.get('TransitGatewayVpcAttachment', {}).get('State')})
            # during this step the associations and propagation are also removed.
            self._create_tag(self.event.get('VpcId'), 'VPCAttachment', 'VPC has been detached from the Transit Gateway')
            self._create_tag(self.event.get('VpcId'), 'VPCAssociation',
                             'VPC has been dissociated with the Transit Gateway Routing Table/Domain')
            self._create_tag(self.event.get('VpcId'), 'VPCPropagation',
                             'VPC RT propagation has been disabled from the '
                             'Transit Gateway Routing Table/Domain')
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('SubnetId'), 'Subnet-Error', e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def _add_subnet_to_tgw_attachment(self, ec2):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info("Add Subnet: {} to Tgw Attachment".format(self.event.get('SubnetId')))
            self.event.update({'Action': 'AddSubnet'})
            response = ec2.add_subnet_to_tgw_attachment(self.event.get('TransitGatewayAttachmentId'),
                                                        self.event.get('SubnetId'))
            if response.get('Error') == 'IncorrectState':
                self.event.update({'AttachmentState': response.get('Error')})
            elif response.get('Error') == 'DuplicateSubnetsInSameZone':
                self.event.update({'Status': 'auto-rejected'})
                comment = "DuplicateSubnetsInSameZoneError: In a TGW VPC attchment, you can add only one subnet per Availability Zone."
                self.event.update({'Comment': comment})
                self._create_tag(self.event.get('SubnetId'), 'Subnet', comment)
            else:
                self._print('Modify (Add Subnet) Transit Gateway Attachment Response', response)
                self.event.update({'AttachmentState': response.get('TransitGatewayVpcAttachment', {}).get('State')})
                self._create_tag(self.event.get('SubnetId'), 'Subnet', 'Subnet appended to the TGW attachment.')
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('SubnetId'), 'Subnet-Error', e)
            raise

    def _remove_subnet_from_tgw_attachment(self, ec2):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info("Remove Subnet: {} from Tgw Attachment".format(self.event.get('SubnetId')))
            self.event.update({'Action': 'RemoveSubnet'})
            response = ec2.remove_subnet_from_tgw_attachment(self.event.get('TransitGatewayAttachmentId'),
                                                             self.event.get('SubnetId'))
            if response.get('Error') == 'IncorrectState':
                self.event.update({'AttachmentState': response.get('Error')})
            # this exception is caught if the last subnet in the attachment is being deleted
            elif response.get('Error') == 'InsufficientSubnetsException':
                self.logger.info('Insufficient Subnets when calling the ModifyTransitGatewayVpcAttachment operation, '
                                 'This is the last subnet in the TGW-VPC Attachment. Deleting TGW Attachment...')
                self.event.update({'Action': 'DeleteTgwVpcAttachment'})
                self._delete_tgw_attachment(ec2)
            else:
                self._print('Modify (Remove Subnet) Transit Gateway Attachment Response', response)
                self.event.update({'AttachmentState': response.get('TransitGatewayVpcAttachment', {}).get('State')})
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('SubnetId'), 'Subnet-Error', e)
            raise

    def tgw_attachment_crud_operations(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)

            # create attachment if TGW Attachment does not exist and Subnet tag exists
            if self.event.get('TgwAttachmentExist') == 'no' and self.event.get('SubnetTagFound') == 'yes':
                self._create_tgw_attachment(ec2)
                self._create_tag(self.event.get('SubnetId'), 'Subnet', 'Subnet added to the TGW attachment.')
                self._create_tag(self.event.get('VpcId'), 'VPCAttachment',
                                 'VPC has been attached to the Transit Gateway')

            # update - add subnet to attachment
            elif self.event.get('FoundExistingSubnetInAttachment') == 'no' and \
                    self.event.get('SubnetTagFound') == 'yes':
                self._add_subnet_to_tgw_attachment(ec2)

            # update - remove subnet from attachment
            # OR
            # delete - if only one subnet left in attachment
            elif self.event.get('FoundExistingSubnetInAttachment') == 'yes' and \
                    self.event.get('SubnetTagFound') == 'no':
                self._remove_subnet_from_tgw_attachment(ec2)
                self._create_tag(self.event.get('SubnetId'), 'Subnet', 'Subnet removed from the TGW attachment.')
            else:
                self.logger.info('No action performed.')

            # find existing TGW route table association to support update action
            self._find_existing_tgw_rt_association(ec2, self.event.get('RouteTableList'))

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('SubnetId'), 'Subnet-Error', e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def _extract_tgw_route_table_names(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])

            # look for defined tag keys in the event
            associate_with, propagate_to = None, None
            for key, value in self.event.items():
                if key.lower().strip() == environ.get('ASSOCIATION_TAG').lower().strip():
                    self.logger.info('Key matched {}:'.format(environ.get('ASSOCIATION_TAG').lower().strip()))
                    self.logger.info("{} : {}".format(key, value))
                    associate_with = value.lower().strip()
                elif key.lower().strip() == environ.get('PROPAGATION_TAG').lower().strip():
                    self.logger.info('Key matched {}:'.format(environ.get('PROPAGATION_TAG').lower().strip()))
                    self.logger.info("{} : {}".format(key, value))
                    propagate_to = [x.lower().strip() for x in value]
            return associate_with, propagate_to
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def describe_transit_gateway_route_tables(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = EC2(self.logger, environ.get('AWS_REGION'))
            # describe tgw route tables for the provided TGW ID
            response = ec2.describe_transit_gateway_route_tables(environ.get('TGW_ID'))
            self._print('Transit Gateway Route Tables', response)

            # returns a tuple (string, list)
            associate_with_table, propagate_to_tables = self._extract_tgw_route_table_names()
            self.logger.info("Table Names in the association: {} | propagation: {}".format(associate_with_table, propagate_to_tables))


            # extract route table ids
            rtb_list = self._extract_route_table_ids(associate_with_table, propagate_to_tables, response)
            self.event.update({'RouteTableList': rtb_list})

            # find existing TGW route table association to support update action
            # needed for 'Association changed?' choice
            self._find_existing_tgw_rt_association(ec2, self.event.get('RouteTableList'))

            # find existing TGW route table propagations
            self.get_transit_gateway_attachment_propagations()

            # set approval flag
            self._set_approval_flag(response)

            # set status based on the approval workflow
            self._set_status()

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _set_approval_flag(self, response):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # set approval required to 'No', assuming if tag is not present it does not require approval
            self.event.update({'ApprovalRequired': 'no'})
            for table in response:
                # iterate through tags for each route table
                for tag in table.get('Tags'):
                    approval_key = environ.get('APPROVAL_KEY')
                    if tag.get('Key').lower().strip() == approval_key.lower().strip():
                        self.logger.info("Found approval tag key set to '{}')".format(tag.get('Value').lower()))
                        if tag.get('Value').lower().strip() == 'yes':
                            # if approval required for this route table change
                            self.logger.info('Any change to this route domain require approval.')
                            self.event.update({table.get('TransitGatewayRouteTableId'): 'approvalrequired'})
            # set approval on association changes
            if self.event.get(self.event.get('AssociationRouteTableId')) == 'approvalrequired':
                # condition to check if already existing associated VPC settings are being changed.
                # example: change in propagation, add or remove subnet.
                if self.event.get('AssociationRouteTableId') == self.event.get('ExistingAssociationRouteTableId'):
                    self.logger.info('Updating other setting for an existing association, no approval required.')
                else:
                    self.logger.info('Found association route table that requires approval')
                    self.event.update({'ApprovalRequired': 'yes'})
                    self.event.update({'AssociationNeedsApproval': 'yes'})

            # set approval on propagation changes
            # iterate through the route table ids with enabled propagations routes tables
            # in the tagging event in the propagate-to key
            for route_table in self.event.get('PropagationRouteTableIds'):
                self.logger.info("<<<<< Set approval on propagation changes for - {}".format(route_table))
                # check if this route table change requires approval
                if self.event.get(route_table) == 'approvalrequired':
                    self.logger.info("Found approval required tag on: {}".format(route_table))
                    if self.event.get('ExistingPropagationRouteTableIds') is not None and \
                            route_table in self.event.get('ExistingPropagationRouteTableIds'):
                        self.logger.info("Route table: {} is not in the existing propagation list,"
                                         " NO approval required.")
                    else:
                        self.logger.info("Route table: {} is not in the existing propagation list. "
                                         "Requires Approval.".format(route_table))
                        self.event.update({'ApprovalRequired': 'yes'})
                        self.event.update({'PropagationNeedsApproval': 'yes'})
                else:
                    self.logger.info(">>>>> Approval not required for Route Table: {}".format(route_table))

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _set_status(self):
        self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
        # needed for 'Requires Approval?' choice in state machine
        if self.event.get('AdminAction') is None:  # valid if VPC or Subnet will be tagged
            self.event.update({'AdminAction': 'not-applicable'})  # set this value to match SM choice
            if self.event.get('ApprovalRequired') == 'yes':  # valid if RT is tagged with ApprovalRequired value
                self.event.update({'Status': 'requested'})  # adds the request to 'Action Items' console page
            elif self.event.get('ApprovalRequired') == 'no':
                self.event.update({'Status': 'auto-approved'})  # adds the request to 'Dashboard' console page
        elif self.event.get('AdminAction') == 'accept':  # valid if event is coming from console action
            self.event.update({'Status': 'approved'})  # adds the request to 'Dashboard' console page
        elif self.event.get('AdminAction') == 'reject':  # valid if event is coming from console action
            self.event.update({'Status': 'rejected'})  # adds the request to 'Dashboard' console page

    def _extract_route_table_ids(self, associate_with_table, propagate_to_tables, response):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            propagate_to_table_ids, rtb_list = [], []
            for table in response:
                # make a list of Route Tables
                rtb_list.append(table.get('TransitGatewayRouteTableId'))
                # iterate through tags for each route table
                for tag in table.get('Tags'):
                    name_key = 'Name'
                    # if tag key is 'Name' then match the value with extracted name from the event
                    if tag.get('Key').lower().strip() == name_key.lower().strip():
                        if associate_with_table is not None:  # handle workflow: if subnet is tagged before vpc
                            # extract route table id for association
                            if tag.get('Value').lower().strip() == associate_with_table:
                                self.logger.info('Association RTB Name found: {}'.format(tag.get('Value')))
                                self.event.update({'AssociationRouteTableId': table.get('TransitGatewayRouteTableId')})
                        else:
                            self.event.update({'AssociationRouteTableId': 'none'})
                        if propagate_to_tables is not None:  # handle workflow: if subnet is tagged before vpc
                            # extract route table id for propagation
                            if tag.get('Value').lower().strip() in propagate_to_tables:
                                self.logger.info('Propagation RTB Name Found: {}'.format(tag.get('Value')))
                                propagate_to_table_ids.append(table.get('TransitGatewayRouteTableId'))
            self.event.update({'PropagationRouteTableIds': propagate_to_table_ids})
            self.logger.info('RTB LIST: {}'.format(rtb_list))
            return rtb_list
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise


    def _find_existing_tgw_rt_association(self, ec2, rtb_list):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.event.update({'ExistingAssociationRouteTableId': 'none'})
            # if transit gateway attachment id is not empty
            if self.event.get('TransitGatewayAttachmentId') is not None:
                response = ec2.describe_transit_gateway_attachments(self.event.get('TransitGatewayAttachmentId'))
                self._print('Describe TGW Attachment Response', response)

                # if route table list is not empty
                if rtb_list:
                    # Check if an existing TGW RT association exists
                    for rtb in rtb_list:
                        # with the filters in the get API, the response list would always have one value, hence using [0]
                        if response:  # in case the response is empty
                            if response[0].get('Association', {}).get('TransitGatewayRouteTableId') == rtb:
                                # update the event with existing RT Id to compare with new RT Id
                                self.logger.info('Found existing association with route table: {}'.format(rtb))
                                self.event.update({'ExistingAssociationRouteTableId': rtb})

                    # identify if the RT association should be created or updated
                    if self.event.get('AssociationRouteTableId') == self.event.get('ExistingAssociationRouteTableId'):
                        self.logger.info('Existing Associated TGW RT and the New TGW RT Id match. No action required.')
                        self.event.update({'UpdateAssociationRouteTableId': 'no'})
                    else:
                        self.logger.info('New TGW RT association found in the event. Update association from {} to {}'
                                         .format(self.event.get('ExistingAssociationRouteTableId'),
                                                 self.event.get('AssociationRouteTableId')))
                        self.event.update({'UpdateAssociationRouteTableId': 'yes'})
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _get_association_state(self, ec2, rtb, status):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            if status != 'associated' or status != 'disassociated':
                flag = True
            else:
                flag = False
            while flag:
                response = ec2.get_transit_gateway_route_table_associations(rtb,
                                                                            self.event.get('TransitGatewayAttachmentId'),
                                                                            self.event.get('VpcId')
                                                                            )
                self._print('Get TGW RT Association Response', response)
                # once the TGW RT is disassociated the returned response is empty list
                if response:
                    status = response[0].get('State')
                else:
                    self.logger.info('Found empty list, the TGW RT disassociated successfully.')
                    status = 'disassociated'
                self.logger.info("Status: {}".format(status))
                if status == 'associated' or status == 'disassociated':
                    flag = False
                self._print('Flag Value', flag)
                sleep(int(environ.get('WAIT_TIME')))
            return status
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def associate_transit_gateway_route_table(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = EC2(self.logger, environ.get('AWS_REGION'))
            if self.event.get('AttachmentState') == 'available':
                self.logger.info('Associating TGW Route Table Id: {}'.format(self.event.get('AssociationRouteTableId')))
                self.event.update({'Action': 'AssociateTgwRouteTable'})
                response = ec2.associate_transit_gateway_route_table(
                    self.event.get('AssociationRouteTableId'),
                    self.event.get('TransitGatewayAttachmentId')
                )
                self._print('TGW Route Table Association Response', response)
                state = self._get_association_state(ec2,
                                                    self.event.get('AssociationRouteTableId'),
                                                    response.get('Association').get('State'))
                self.event.update({'AssociationState': state})
                self._create_tag(self.event.get('VpcId'), 'VPCAssociation',
                                 'VPC has been associated with the Transit Gateway Routing Table/Domain')
            else:
                self.logger.info("The TGW-VPC Attachment is not in 'available'")
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def disassociate_transit_gateway_route_table(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = EC2(self.logger, environ.get('AWS_REGION'))
            if self.event.get('AttachmentState') == 'available':
                self.logger.info('Disassociating TGW Route Table Id: {}'.
                                 format(self.event.get('ExistingAssociationRouteTableId')))
                self.event.update({'Action': 'DisassociateTgwRouteTable'})
                response = ec2.disassociate_transit_gateway_route_table(
                    self.event.get('ExistingAssociationRouteTableId'),
                    self.event.get('TransitGatewayAttachmentId')
                )
                self._print('TGW Route Table Dissociation Response', response)
                state = self._get_association_state(ec2,
                                                    self.event.get('ExistingAssociationRouteTableId'),
                                                    response.get('Association').get('State'))
                self.event.update({'DisassociationState': state})
                self._create_tag(self.event.get('VpcId'), 'VPCAssociation',
                                 'VPC has been dissociated with the Transit Gateway Routing Table/Domain')
            else:
                self.logger.info("The TGW-VPC Attachment is not in 'available'")
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def get_transit_gateway_attachment_propagations(self):
        try:
            if self.event.get('AttachmentState') == 'available':
                self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
                ec2 = EC2(self.logger, environ.get('AWS_REGION'))
                response = ec2.get_transit_gateway_attachment_propagations(self.event.get('TransitGatewayAttachmentId'))
                self._print('Get TGW Route Table Propagation Response', response)

                existing_route_table_list = []
                if response:
                    for item in response:
                        existing_route_table_list.append(item.get('TransitGatewayRouteTableId'))
                self.event.update({'ExistingPropagationRouteTableIds': existing_route_table_list})
            else:
                self.logger.info("The TGW-VPC Attachment is not in 'available'")
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _enable_rtb_list(self):
        event_set = set(self.event.get('PropagationRouteTableIds'))
        existing_set = set(self.event.get('ExistingPropagationRouteTableIds'))
        enable_rtb_list = list(event_set - event_set.intersection(existing_set))
        return enable_rtb_list

    def enable_transit_gateway_route_table_propagation(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = EC2(self.logger, environ.get('AWS_REGION'))
            if self.event.get('AttachmentState') == 'available':
                enable_route_table_propagation = self._enable_rtb_list()
                self.event.update({'EnablePropagationRouteTableIds': enable_route_table_propagation})
                # if the return list is empty the API to enable tgw rt propagation will be skipped.
                for tgw_route_table_id in enable_route_table_propagation:
                    self.logger.info("Enabling RT: {} Propagation To Tgw Attachment".format(tgw_route_table_id))
                    self.event.update({'Action': 'EnableTgwRtPropagation'})
                    response = ec2.enable_transit_gateway_route_table_propagation(
                        tgw_route_table_id,
                        self.event.get('TransitGatewayAttachmentId')
                    )
                    self._print('TGW Route Table Enable Propagation Response', response)
                    self._create_tag(self.event.get('VpcId'), 'VPCPropagation',
                                     'VPC RT propagation has been enabled to the Transit Gateway Routing Table/Domain')
            else:
                self.logger.info("The TGW-VPC Attachment is not in 'available'")
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def _disable_rtb_list(self):
        event_set = set(self.event.get('PropagationRouteTableIds'))
        existing_set = set(self.event.get('ExistingPropagationRouteTableIds'))
        disable_rtb_list = list(event_set.union(existing_set) - event_set)
        return disable_rtb_list

    def disable_transit_gateway_route_table_propagation(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = EC2(self.logger, environ.get('AWS_REGION'))
            if self.event.get('AttachmentState') == 'available':
                disable_route_table_propagation = self._disable_rtb_list()
                self.event.update({'DisablePropagationRouteTableIds': disable_route_table_propagation})
                # if the return list is empty the API to disable tgw rt propagation will be skipped.
                for tgw_route_table_id in disable_route_table_propagation:
                    self.logger.info("Disabling RT: {} Propagation From Tgw Attachment".format(tgw_route_table_id))
                    self.event.update({'Action': 'DisableTgwRtPropagation'})
                    response = ec2.disable_transit_gateway_route_table_propagation(
                        tgw_route_table_id,
                        self.event.get('TransitGatewayAttachmentId')
                    )
                    self._print('TGW Route Table Disable Propagation Response', response)
                    self._create_tag(self.event.get('VpcId'), 'VPCPropagation',
                                     'VPC RT propagation has been disabled from the '
                                     'Transit Gateway Routing Table/Domain')
            else:
                self.logger.info("The TGW-VPC Attachment is not in 'available'")
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('VpcId'), 'VPC-Error', e)
            raise

    def _update_ddb_failed(self, e):
        self.event.update({'Comment': str(e)})
        self.event.update({'Status': 'failed'})
        ddb = DynamoDb(self.event, self.logger)
        ddb.put_item()


class VPC(object):
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.assume_role = AssumeRole()
        self.spoke_account_id = self.event.get('account')
        self.spoke_region = self.event.get('region')
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return EC2(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def _print(self, description, response):
        self.logger.info('Printing {}'.format(description))
        self.logger.info(response)

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)
            ec2.create_tags(resource, 'STNOStatus-' + key, timestamp_message(message))
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def _extract_resource_id(self):
        resource_arn = self.event.get('resources')[0]
        return resource_arn.split('/')[1]

    def _check_list_length(self, array, length):
        # compare the length of the list
        if len(array) == length:
            return None
        else:
            raise Exception("Length of the list in the response is more than {} values.".format(length))

    def describe_resources(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # check if the event is coming from STNO Management Console
            if self.event.get('AdminAction') is None:
                # extract subnet id from the ARN
                resource_id = self._extract_resource_id()
                # if event is from VPC tagging
                if resource_id.startswith("vpc"):
                    self.logger.info('Tag Change on VPC: {}'.format(resource_id))
                    self.event.update({'VpcId': resource_id})
                    self.event.update({'TagEventSource': 'vpc'})
                    # get VPC details
                    self._describe_vpc()
                # if event from Subnet tagging
                elif resource_id.startswith("subnet"):
                    self.logger.info('Tag Change on Subnet: {}'.format(resource_id))
                    self.event.update({'SubnetId': resource_id})
                    self.event.update({'TagEventSource': 'subnet'})
                    # get subnet details
                    self._describe_subnet()
                    # get VPC details
                    self._describe_vpc()
                else:
                    self.logger.info('Resource Id is neither a VPC nor a subnet.')
                    raise Exception('Application Exception: Resource Id is neither a VPC nor a subnet.')
            elif self.event.get('TagEventSource') == 'vpc':
                self._set_event_variables()
                # get VPC details
                self._describe_vpc()
            elif self.event.get('TagEventSource') == 'subnet':
                self._set_event_variables()
                # get subnet details
                self._describe_subnet()
                # get VPC details
                self._describe_vpc()

            if self.event.get('time') is None:
                self.event.update({'time': current_time()})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _set_event_variables(self):
        self.logger.info('Event came from the management console, setting variables')
        self.event.update({'account': self.event.get('AWSSpokeAccountId')})
        self.event.update({environ.get('ASSOCIATION_TAG'): self.event.get('AssociationRouteTable')})
        self.event.update({environ.get('PROPAGATION_TAG'): self.event.get('PropagationRouteTables')})

        # re-initialize the class variables
        self._reset()

    def _reset(self):
        # reset class variables
        self.__init__(self.event, self.logger)

    def _describe_vpc(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)

            # describe the vpc in the spoke account
            response = ec2.describe_vpcs(self.event.get('VpcId'))
            self._print('Describe VPC', response)

            # the response should return a list with single item
            self._check_list_length(response, 1)

            # update event with subnet details
            index = 0
            vpc = response[index]

            # Cidr block associated with this VPC
            self.event.update({'VpcCidr': vpc.get('CidrBlock')})

            # Assuming VPC is not tagged
            self.event.update({'VpcTagFound': 'no'})

            tag_key_list = []
            if vpc.get('Tags') is not None:
                for tag in vpc.get('Tags'):
                    tag_key_list.append(tag.get('Key').lower().strip())
                self._print('list of tag keys', tag_key_list)
            else:
                self.logger.info("No tags found for the VPC associated with the tagged Subnet.")

            if tag_key_list is not None:
                # check if tags exist for the VPC
                if environ.get('ASSOCIATION_TAG').lower().strip() in tag_key_list or \
                        environ.get('PROPAGATION_TAG').lower().strip() in tag_key_list:
                    self.logger.info('Found association or propagation tag for the VPC: {}'.format(self.event.get('VpcId')))
                    self.event.update({'VpcTagFound': 'yes'})

            # event source is subnet tag change, then obtain the Tag Event Sources from VPC tags
            if self.event.get('TagEventSource') == 'subnet':
                self._update_event_with_vpc_tags(vpc.get('Tags'))
            else:
                self._update_event_with_vpc_tags(self.event.get('detail', {}).get('tags'))

            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _match_keys_with_tag(self, key, value):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            if key.lower().strip() == environ.get('ASSOCIATION_TAG').lower().strip():
                self.event.update({environ.get('ASSOCIATION_TAG'): value.lower().strip()})
                self._print("Modified Event with Association Tag", self.event)
            elif key.lower().strip() == environ.get('PROPAGATION_TAG').lower().strip():
                value = value.split(",")  # convert comma delimited string to list
                self.event.update({environ.get('PROPAGATION_TAG'): [x.lower().strip() for x in value]})
                self._print("Modified Event with Propagation Tag", self.event)
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _update_event_with_vpc_tags(self, tags):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info("Update event with VPC tags if the event source is 'Subnet'")
            if isinstance(tags, list):
                for tag in tags:
                    self._match_keys_with_tag(tag.get('Key'), tag.get('Value'))
            elif isinstance(tags, dict):
                for key, value in tags.items():
                    self._match_keys_with_tag(key, value)

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _describe_subnet(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)

            # describe the subnet
            response = ec2.describe_subnets(self.event.get('SubnetId'))
            self._print('Describe Subnet', response)

            # the response should return a list with single item
            self._check_list_length(response, 1)

            # update event with subnet details
            index = 0
            subnet = response[index]

            # vpc id associated with this subnet
            self.event.update({'VpcId': subnet.get('VpcId')})

            # availability zone
            self.event.update({'AvailabilityZone': subnet.get('AvailabilityZone')})

            tag_key_list = []
            for tag in subnet.get('Tags'):
                tag_key_list.append(tag.get('Key').lower().strip())
            self._print('list of tag keys', tag_key_list)

            # check of tags exist for the subnet
            if environ.get('ATTACHMENT_TAG').lower().strip() in tag_key_list:
                self.logger.info('Found attachment tag for the subnet: {}'.format(self.event.get('SubnetId')))
                # help us decide if we can remove this subnet from the attachment
                self.event.update({'SubnetTagFound': 'yes'})
            else:
                self.event.update({'SubnetTagFound': 'no'})
            return self.event
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _describe_route_tables_for_subnet(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)

            # describe the explicit route table association with the subnet
            response = ec2.describe_route_tables_for_subnet(self.event.get('SubnetId'))
            self._print('Describe Route Table for Subnets', response)

            # handle scenario of there is no EXPLICIT ASSOCIATION between the subnet and route table
            if len(response) != 0:
                # update event with subnet details
                index = 0
                route_table = response[index]

                # route table associated with this subnet
                self.event.update({'RouteTableId': route_table.get('RouteTableId')})
                routes = route_table.get('Routes')
                return routes
            else:
                self.logger.info("There is no explicit route table association with the tagged subnet: {}"
                                 .format(self.event.get('SubnetId')))
                self.event.update({'RouteTableId': 'No-Explicit-RT'})
                return None

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _find_existing_default_route(self, existing_routes, destination_route):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            gateway_id = None
            # set default flags
            self.event.update({'DefaultRouteToTgwExists': 'no'})
            self.event.update({'DestinationRouteExists': 'no'})
            for route in existing_routes:
                if route.get('DestinationCidrBlock') == destination_route:
                    # if destination route already exists in the route table - set flag
                    self.event.update({'DestinationRouteExists': 'yes'})
                    self.logger.info('Found route: {} in the route table.'.format(destination_route))
                    # Check if default route has Transit gateway as the target
                    if route.get('TransitGatewayId') is not None:
                        comment = "Found Transit Gateway as a target to the default route: {}" \
                            .format(destination_route)
                        self.event.update({'DefaultRouteToTgwExists': 'yes'})
                        self.logger.info(comment)
                        gateway_id = route.get('TransitGatewayId')
                        self._print('Transit Gateway Id', gateway_id)

                    # Check if default route has Internet gateway as the target
                    elif route.get('GatewayId') is not None:
                        comment = "Found existing gateway as a target to the default route: {}" \
                            .format(destination_route)
                        self.logger.info(comment)
                        gateway_id = route.get('GatewayId')
                        self._print('Gateway Id', gateway_id)

                    # Check if default route has NAT gateway as the target
                    elif route.get('NatGatewayId') is not None:
                        comment = "Found NAT Gateway as a target to the default route: {}" \
                            .format(destination_route)
                        self.logger.info(comment)
                        gateway_id = route.get('NatGatewayId')
                        self._print('NAT Gateway Id', gateway_id)
                    elif route.get('VpcPeeringConnectionId') is not None:
                        comment = "Found VPC Peering Connection as a target to the default route: {}" \
                            .format(destination_route)
                        self.logger.info(comment)
                        gateway_id = route.get('VpcPeeringConnectionId')
                        self._print('Peering Connection Id', gateway_id)
                    else:
                        self.logger.info("Found an existing target for the default route.")
                        gateway_id = 'custom-target'
                        self._print('Route', route)
            # update event with gateway id
            self.event.update({'GatewayId': gateway_id})
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _create_route(self, ec2, destination):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            if self.event.get('DefaultRouteToTgwExists') == 'no' and self.event.get('DestinationRouteExists') == 'no':
                self.logger.info("Adding destination route: {} to TGW gateway: {} into the route table: {}"
                                 .format(destination, environ.get('TGW_ID'), self.event.get('RouteTableId')))
                ec2.create_route(destination, self.event.get('RouteTableId'), environ.get('TGW_ID'))
                self._create_tag(self.event.get('RouteTableId'), 'RouteTable', 'Route(s) added to the route table.')
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('RouteTableId'), 'RouteTable-Error', e)
            raise

    def _delete_route(self, ec2, destination):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            if self.event.get('DefaultRouteToTgwExists') == 'yes' and self.event.get('DestinationRouteExists') == 'yes':
                self.logger.info("Removing destination route: {} to TGW gateway: {} from the route table: {}"
                                 .format(destination, environ.get('TGW_ID'), self.event.get('RouteTableId')))
                ec2.delete_route(destination, self.event.get('RouteTableId'))
                self._create_tag(self.event.get('RouteTableId'), 'RouteTable', 'Route(s) removed from the route table.')
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            self._create_tag(self.event.get('RouteTableId'), 'RouteTable-Error', e)
            raise

    def _update_route_table(self, ec2, route):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # if adding subnet to tgw attachment - create route
            # else if removing subnet from tgw attachment - delete route
            if self.event.get('Action') == 'AddSubnet' or self.event.get('Action') == 'CreateTgwVpcAttachment':
                # create route in spoke account route table
                self._create_route(ec2, route)
            elif self.event.get('Action') == 'RemoveSubnet' or self.event.get('Action') == 'DeleteTgwVpcAttachment':
                # delete route from spoke account route table
                self._delete_route(ec2, route)
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def default_route_crud_operations(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # this condition will be met if VPC tagged not Subnet
            if self.event.get('SubnetId') is not None:
                ec2 = self._session(self.spoke_region, self.spoke_account_id)

                existing_routes = self._describe_route_tables_for_subnet()

                # handles the case if the subnet has no association with explicit route table
                if existing_routes is None:
                    return self.event

                # allowed values in hub CFN template
                # "All-Traffic (0/0)"
                # "RFC-1918 (10/8, 172.16/12, 192.168/16)"
                # "Configure-Manually

                if "All-Traffic" in environ.get('DEFAULT_ROUTE'):
                    self._find_existing_default_route(existing_routes, environ.get('ALL_TRAFFIC'))
                    self._update_route_table(ec2, environ.get('ALL_TRAFFIC'))
                elif "RFC-1918" in environ.get('DEFAULT_ROUTE'):
                    for route in [x.strip() for x in environ.get('RFC_1918_ROUTES').split(',')]:
                        self._find_existing_default_route(existing_routes, route)
                        self._update_route_table(ec2, route)
                elif "Configure-Manually" in environ.get('DEFAULT_ROUTE'):
                    self.logger.info('Admin opted to configure route table manually')

            return self.event

        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _message(self, method, e):
        return {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                'METHOD': method, 'EXCEPTION': str(e)}

    def _update_ddb_failed(self, e):
        self.event.update({'Comment': str(e)})
        self.event.update({'Status': 'failed'})
        ddb = DynamoDb(self.event, self.logger)
        ddb.put_item()


class DynamoDb(object):
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _get_time_to_live(self, time):
        utc_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
        orig = datetime.fromtimestamp(int(epoch_time))
        ttl = orig + timedelta(days=int(environ.get('TTL')))
        return str(int((ttl - datetime(1970, 1, 1)).total_seconds()))

    # return None (string type) if the value is NoneType
    def is_none(self, value):
        if value is None:
            return 'None'
        else:
            return value

    def put_item(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ddb = DDB(self.logger, environ.get('TABLE_NAME'))

            item = {
                "SubnetId": self.is_none(self.event.get('SubnetId')),
                "Version": self.is_none(str(self.event.get('detail', {}).get('version'))),
                "AvailabilityZone": self.is_none(self.event.get('AvailabilityZone')),
                "VpcId": self.is_none(self.event.get('VpcId')),
                "TgwId": self.is_none(environ.get('TGW_ID')),
                "PropagationRouteTables": self.event.get(environ.get('PROPAGATION_TAG')),
                "PropagationRouteTablesString": 'None' if self.event.get(environ.get('PROPAGATION_TAG')) is None else ','.join(self.event.get(environ.get('PROPAGATION_TAG'))),
                "TagEventSource": self.is_none(self.event.get('TagEventSource')),
                "VpcCidr": self.is_none(self.event.get('VpcCidr')),
                "Action": self.is_none(self.event.get('Action')),
                "Status": self.is_none(self.event.get('Status')),
                "AWSSpokeAccountId": self.is_none(self.event.get('account')),
                "UserId": "StateMachine" if self.event.get('UserId') is None else self.event.get('UserId'),
                "AssociationRouteTable": self.event.get(environ.get('ASSOCIATION_TAG')),
                "RequestTimeStamp": self.event.get('time'),
                "ResponseTimeStamp": current_time() if self.event.get(
                    'GraphQLTimeStamp') is None else self.event.get('GraphQLTimeStamp'),
                "TimeToLive": self._get_time_to_live(self.event.get('time')),
                "Comment": self.is_none(self.event.get('Comment'))
            }

            self.logger.info(item)
            # add item to the DDB table with version in event
            ddb.put_item(item)

            item.update({'Version': 'latest'})
            ddb.put_item(item)

            # send anonymous metrics
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_anonymous_data()

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

class ApprovalNotification(object):
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.spoke_account_id = self.event.get('account')
        self.spoke_region = environ.get('AWS_REGION')
        self.assume_role = AssumeRole()
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return EC2(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def notify(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            if environ.get('APPROVAL_NOTIFICATION').lower() == 'yes' and self.event.get('Status') == 'requested':
                self._send_email()
                self.logger.info("Adding tag to VPC with the pending approval message")
                if self.event.get('AssociationNeedsApproval') == 'yes':
                    self._create_tag(self.event.get('VpcId'), 'VPCAssociation',
                                     'Request to associate this VPC with requested TGW Routing Table is PENDING APPROVAL. '
                                     'Contact your network admin for more information.')
                if self.event.get('PropagationNeedsApproval') == 'yes':
                    self._create_tag(self.event.get('VpcId'), 'VPCPropagation',
                                     'Request to propagate this VPC to requested TGW Routing Table is PENDING APPROVAL. '
                                     'Contact your network admin for more information.')
            elif self.event.get('Status') == 'rejected':
                self.logger.info("Adding tag to VPC with the rejection message")
                if self.event.get('AssociationNeedsApproval') == 'yes':
                    self._create_tag(self.event.get('VpcId'), 'VPCAssociation',
                                     'Request to associate this VPC with requested TGW Routing Table has been REJECTED. '
                                     'Contact your network admin for more information.')
                if self.event.get('PropagationNeedsApproval') == 'yes':
                    self._create_tag(self.event.get('VpcId'), 'VPCPropagation',
                                     'Request to propagate this VPC to requested TGW Routing Table has been REJECTED. '
                                     'Contact your network admin for more information. ')
            else:
                self.logger.info("Approval notifications are disabled. Please set CFN template variable "
                                 "'ApprovalNotification' to 'Yes' if you wish to receive notifications.")
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _send_email(self):
        notify = SNS(self.logger)
        topic_arn = environ.get('APPROVAL_NOTIFICATION_ARN')
        subject = "STNO: Transit Network Change Requested"
        message = "A new request for VPC: '{}' to associate with TGW Route Table: '{}' and propagate to " \
                  "TGW Route Tables: '{}' is ready for review. Please use this link {} to login to the 'Transit Network " \
                  "Management Console' to approve or reject the request.".format(self.event.get('VpcId'),
                                                                                 self.event.get('Associate-with').title(),
                                                                                 ', '.join(self.event.get('Propagate-to')).title(),
                                                                                 environ.get('STNO_CONSOLE_LINK'))
        self.logger.info("Message: {}".format(message))
        notify.publish(topic_arn, message, subject)
        self.logger.info('Notfication sent to the network admin for approval.')

    def _create_tag(self, resource, key, message):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            ec2 = self._session(self.spoke_region, self.spoke_account_id)
            ec2.create_tags(resource, 'STNOStatus-' + key, timestamp_message(message))
        except Exception as e:
            message = self._message(inspect.stack()[0][3], e)
            self.logger.exception(message)

    def _message(self, method, e):
        return {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                'METHOD': method, 'EXCEPTION': str(e)}

    def _update_ddb_failed(self, e):
        self.event.update({'Comment': str(e)})
        self.event.update({'Status': 'failed'})
        ddb = DynamoDb(self.event, self.logger)
        ddb.put_item()

class ResourceAccessManager(object):
    """
    This class contains functions to manage VPC related resources
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.assume_role = AssumeRole()
        self.spoke_account_id = self.event.get('account')
        self.spoke_region = self.event.get('region')
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return RAM(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def _print(self, description, response):
        self.logger.info('Printing {}'.format(description))
        self.logger.info(response)

    def _hub_account_id(self):
        sts = STS(self.logger)
        return sts.get_account_id()

    ''' This function accepts resource invitation in the spoke account. This is applicable
     to the scenario if the accounts are not in the AWS Organization.'''

    def accept_resource_share_invitation(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])

            # check if the accounts are in the organization
            check_invitation_status = True
            if 'arn:aws:organizations' in environ.get('FIRST_PRINCIPAL'):
                check_invitation_status = False

            # check the invitation status if the accounts are not in AWS Organization
            if check_invitation_status:
                # accept resource share invitation
                ram = self._session(self.spoke_region, self.spoke_account_id)
                # get resource share invitations
                invitation_list = ram.get_resource_share_invitations(environ.get('RESOURCE_SHARE_ARN'))
                self.logger.debug('Get Resource Share Invitation Response')
                self.logger.debug(invitation_list)  # would always be single item in the response list
                for invitation in invitation_list:
                    # parse the invitation id arn to accept the invitation
                    if invitation.get('status') == 'PENDING' and invitation.get(
                            'senderAccountId') == self._hub_account_id():
                        response = ram.accept_resource_share_invitation(invitation.get('resourceShareInvitationArn'))
                        self._print("Accept Resource Share Response", response)
                        self.event.update({'ResourceShareArnAccepted': invitation.get('resourceShareArn')})
                    else:
                        self.logger.info('PENDING resource share not found in the spoke account.')
                        self.event.update({'ResourceShareArnAccepted': invitation.get('None')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            self._update_ddb_failed(e)
            raise

    def _update_ddb_failed(self, e):
        self.event.update({'Comment': str(e)})
        self.event.update({'Status': 'failed'})
        ddb = DynamoDb(self.event, self.logger)
        ddb.put_item()


class GeneralFunctions(object):
    """
    This class contains functions that serves general purposes.
    """

    def __init__(self, event, logger):
        self.event = event
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    # return None (string type) if the value is NoneType
    def is_none(self, value):
        if value is None:
            return 'None'
        else:
            return value

    def send_anonymous_data(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            send = Metrics(self.logger)
            data = {
                "Action": self.is_none(self.event.get('Action')),
                "Status": self.is_none(self.event.get('Status')),
                "AdminAction": self.is_none(self.event.get('AdminAction')),
                "ApprovalRequired": self.is_none(self.event.get('ApprovalRequired')),
                "TagEventSource": self.is_none(self.event.get('TagEventSource')),
                "Region": self.is_none(self.event.get('region')),
                "SolutionVersion": self.is_none(environ.get('SOLUTION_VERSION'))
            }
            send.metrics(data)
            return self.event
        except:
            return self.event

