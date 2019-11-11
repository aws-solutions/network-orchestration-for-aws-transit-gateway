######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################
#!/bin/python
from botocore.exceptions import ClientError
from lib.decorator import try_except_retry
import boto3
import inspect


class EC2(object):
    def __init__(self, logger, region, **kwargs):
        self.logger = logger
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up EC2 BOTO3 Client with default credentials")
                self.ec2_client = boto3.client('ec2', region_name=region)
            else:
                logger.debug("Setting up EC2 BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                self.ec2_client = boto3.client('ec2', region_name=region,
                                               aws_access_key_id=cred.get('AccessKeyId'),
                                               aws_secret_access_key=cred.get('SecretAccessKey'),
                                               aws_session_token=cred.get('SessionToken')
                                               )
        else:
            logger.info("There were no keyworded variables passed.")
            self.ec2_client = boto3.client('ec2', region_name=region)

    @try_except_retry()
    def describe_regions(self):
        try:
            response = self.ec2_client.describe_regions()
            return response.get('Regions')
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_vpcs(self, vpc_id):
        try:
            response = self.ec2_client.describe_vpcs(
                VpcIds=[vpc_id]
            )

            vpc_list = response.get('Vpcs', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.describe_subnets(
                    VpcIds=[vpc_id],
                    NextToken=next_token
                )
                vpc_list.extend(response.get('Vpcs', []))
                next_token = response.get('NextToken', None)

            return vpc_list  # return list - should contain only one item in the list
        except ClientError as e:
            if e.response['Error']['Code'] == 'OptInRequired':
                self.logger.info("Caught exception 'OptInRequired', handling the exception...")
                return {"Error": "OptInRequired"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    @try_except_retry()
    def describe_subnets(self, subnet_id):
        try:
            response = self.ec2_client.describe_subnets(
                SubnetIds=[subnet_id]
            )

            subnet_list = response.get('Subnets', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.describe_subnets(
                    SubnetIds=[subnet_id],
                    NextToken=next_token
                )
                subnet_list.extend(response.get('Subnets', []))
                next_token = response.get('NextToken', None)

            return subnet_list  # return list - should contain only one item in the list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_internet_gateways(self, vpc_id):
        try:
            response = self.ec2_client.describe_internet_gateways(
                Filters=[
                    {
                        'Name': 'attachment.vpc-id',
                        'Values': [
                            vpc_id,
                        ],
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_availability_zones(self):
        try:
            response = self.ec2_client.describe_availability_zones(Filters=[{'Name': 'state', 'Values': ['available']}])
            return [r['ZoneName'] for r in response['AvailabilityZones']]
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_route(self, vpc_cidr, route_table_id, transit_gateway_id):
        try:
            response = self.ec2_client.create_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id,
                TransitGatewayId=transit_gateway_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_route(self, vpc_cidr, route_table_id):
        try:
            response = self.ec2_client.delete_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def replace_route(self, vpc_cidr, route_table_id, transit_gateway_id):
        try:
            response = self.ec2_client.replace_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id,
                TransitGatewayId=transit_gateway_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_route_tables_for_subnet(self, subnet_id):
        try:
            response = self.ec2_client.describe_route_tables(
                Filters=[
                            {
                                'Name': 'association.subnet-id',
                                'Values': [subnet_id]
                            }
                        ]
            )

            route_table_list = response.get('RouteTables', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.describe_route_tables(
                    Filters=[
                        {
                            'Name': 'association.subnet-id',
                            'Values': [subnet_id]
                        }
                    ],
                    NextToken=next_token
                )
                route_table_list.extend(response.get('RouteTables', []))
                next_token = response.get('NextToken', None)

            return route_table_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def associate_transit_gateway_route_table(self, transit_gateway_route_table_id, transit_gateway_attachment_id):
        try:
            response = self.ec2_client.associate_transit_gateway_route_table(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_transit_gateway_vpc_attachment(self, tgw_id, vpc_id, subnet_id):
        """
        :param tgw_id:
        :param vpc_id:
        :param subnet_id:
        :return:
            {
            'TransitGatewayVpcAttachment': {
                'TransitGatewayAttachmentId': 'string',
                'TransitGatewayId': 'string',
                'VpcId': 'string',
                'VpcOwnerId': 'string',
                'State': 'pendingAcceptance'|'rollingBack'|'pending'|'available'|'modifying'|'deleting'|'deleted'
                |'failed'|'rejected'|'rejecting'|'failing',
                'SubnetIds': [
                    'string',
                ],
                'CreationTime': datetime(2015, 1, 1),
                'Options': {
                    'DnsSupport': 'enable'|'disable',
                    'Ipv6Support': 'enable'|'disable'
                },
                'Tags': [
                    {
                        'Key': 'string',
                        'Value': 'string'
                    },
                ]
            }
        }
        """
        try:
            response = self.ec2_client.create_transit_gateway_vpc_attachment(
                TransitGatewayId=tgw_id,
                VpcId=vpc_id,
                SubnetIds=[
                    subnet_id
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_transit_gateway_vpc_attachment(self, tgw_attachment_id):
        """
        :param tgw_attachment_id:
        :return:
            {
                'TransitGatewayVpcAttachment': {
                    'TransitGatewayAttachmentId': 'string',
                    'TransitGatewayId': 'string',
                    'VpcId': 'string',
                    'VpcOwnerId': 'string',
                    'State': 'pendingAcceptance'|'rollingBack'|'pending'|'available'|'modifying'|'deleting'|'deleted'
                    |'failed'|'rejected'|'rejecting'|'failing',
                    'SubnetIds': [
                        'string',
                    ],
                    'CreationTime': datetime(2015, 1, 1),
                    'Options': {
                        'DnsSupport': 'enable'|'disable',
                        'Ipv6Support': 'enable'|'disable'
                    },
                    'Tags': [
                        {
                            'Key': 'string',
                            'Value': 'string'
                        },
                    ]
                }
            }
        """
        try:
            response = self.ec2_client.delete_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def get_transit_gateway_vpc_attachment_state(self, tgw_attachment_id):
        try:
            response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                TransitGatewayAttachmentIds=[
                    tgw_attachment_id
                ]
            )

            transit_gateway_vpc_attachments_list = response.get('TransitGatewayVpcAttachments', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                self.logger.info("Next Token Returned: {}".format(next_token))
                response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                    TransitGatewayAttachmentIds=[
                        tgw_attachment_id
                    ],
                    NextToken=next_token
                )
                self.logger.info("Extending TGW-VPC Attachment List")
                transit_gateway_vpc_attachments_list.extend(response.get('TransitGatewayVpcAttachments', []))
                next_token = response.get('NextToken', None)

            return transit_gateway_vpc_attachments_list

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_transit_gateway_vpc_attachments(self, tgw_id, vpc_id, state):
        try:
            response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                Filters=[
                    {
                        'Name': 'transit-gateway-id',
                        'Values': [tgw_id]
                    },
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    },
                    {
                        'Name': 'state',
                        'Values': state
                    }
                ]
            )

            transit_gateway_vpc_attachments_list = response.get('TransitGatewayVpcAttachments', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                self.logger.info("Next Token Returned: {}".format(next_token))
                response = self.ec2_client.describe_transit_gateway_vpc_attachments(
                    Filters=[
                        {
                            'Name': 'transit-gateway-id',
                            'Values': [tgw_id]
                        },
                        {
                            'Name': 'vpc-id',
                            'Values': [vpc_id]
                        },
                        {
                            'Name': 'state',
                            'Values': state
                        }
                    ],
                    NextToken=next_token
                )
                self.logger.info("Extending TGW-VPC Attachment List")
                transit_gateway_vpc_attachments_list.extend(response.get('TransitGatewayVpcAttachments', []))
                next_token = response.get('NextToken', None)

            return transit_gateway_vpc_attachments_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_transit_gateway_attachments(self, transit_gateway_attachment_id):  #, tgw_id, vpc_id):
        try:
            response = self.ec2_client.describe_transit_gateway_attachments(
                TransitGatewayAttachmentIds=[transit_gateway_attachment_id]
            )

            transit_gateway_attachments_list = response.get('TransitGatewayAttachments', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                self.logger.info("Next Token Returned: {}".format(next_token))
                response = self.ec2_client.describe_transit_gateway_attachments(
                    TransitGatewayAttachmentIds=[transit_gateway_attachment_id],
                    NextToken=next_token
                )
                self.logger.info("Extending TGW Attachment List")
                transit_gateway_attachments_list.extend(response.get('TransitGatewayAttachments', []))
                next_token = response.get('NextToken', None)

            return transit_gateway_attachments_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_transit_gateway_route_tables(self, tgw_id):
        try:
            response = self.ec2_client.describe_transit_gateway_route_tables(
                Filters=[
                    {
                        'Name': 'transit-gateway-id',
                        'Values': [tgw_id]
                    }
                ]
            )

            route_table_list = response.get('TransitGatewayRouteTables', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.describe_transit_gateway_route_tables(
                    Filters=[
                        {
                            'Name': 'transit-gateway-id',
                            'Values': [tgw_id]
                        }
                    ],
                    NextToken=next_token
                )
                route_table_list.extend(response.get('TransitGatewayRouteTables', []))
                next_token = response.get('NextToken', None)
            return route_table_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def disable_transit_gateway_route_table_propagation(self, transit_gateway_route_table_id, transit_gateway_attachment_id):
        try:
            response = self.ec2_client.disable_transit_gateway_route_table_propagation(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def disassociate_transit_gateway_route_table(self, transit_gateway_route_table_id, transit_gateway_attachment_id):
        try:
            response = self.ec2_client.disassociate_transit_gateway_route_table(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def enable_transit_gateway_route_table_propagation(self, transit_gateway_route_table_id, transit_gateway_attachment_id):
        try:
            response = self.ec2_client.enable_transit_gateway_route_table_propagation(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                TransitGatewayAttachmentId=transit_gateway_attachment_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def get_transit_gateway_attachment_propagations(self, transit_gateway_attachment_id):
        try:
            response = self.ec2_client.get_transit_gateway_attachment_propagations(
                TransitGatewayAttachmentId=transit_gateway_attachment_id
            )
            propagations_list = response.get('TransitGatewayAttachmentPropagations', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.get_transit_gateway_attachment_propagations(
                    TransitGatewayAttachmentId=transit_gateway_attachment_id,
                    NextToken=next_token
                )
                propagations_list.extend(response.get('TransitGatewayAttachmentPropagations', []))
                next_token = response.get('NextToken', None)
            return propagations_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def get_transit_gateway_route_table_associations(self, transit_gateway_route_table_id,
                                                     transit_gateway_attachment_id,
                                                     resource_id,
                                                     resource_type='vpc'):
        try:
            response = self.ec2_client.get_transit_gateway_route_table_associations(
                TransitGatewayRouteTableId=transit_gateway_route_table_id,
                Filters=[
                    {
                        'Name': 'transit-gateway-attachment-id',
                        'Values': [transit_gateway_attachment_id]
                    },
                    {
                        'Name': 'resource-type',
                        'Values': [resource_type]
                    },
                    {
                        'Name': 'resource-id',
                        'Values': [resource_id]
                    }
                ]
            )

            associations_list = response.get('Associations', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.get_transit_gateway_route_table_associations(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    NextToken=next_token
                )
                associations_list.extend(response.get('Associations', []))
                next_token = response.get('NextToken', None)
            return associations_list

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def get_transit_gateway_route_table_propagations(self, transit_gateway_route_table_id):
        try:
            response = self.ec2_client.get_transit_gateway_route_table_propagations(
                TransitGatewayRouteTableId=transit_gateway_route_table_id
            )
            propagations_list = response.get('TransitGatewayRouteTablePropagations', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                response = self.ec2_client.get_transit_gateway_attachment_propagations(
                    TransitGatewayRouteTableId=transit_gateway_route_table_id,
                    NextToken=next_token
                )
                propagations_list.extend(response.get('TransitGatewayRouteTablePropagations', []))
                next_token = response.get('NextToken', None)
            return propagations_list
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def add_subnet_to_tgw_attachment(self, tgw_attachment_id, subnet_id):
        try:
            response = self.ec2_client.modify_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id,
                AddSubnetIds=[
                    subnet_id
                ]
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'IncorrectState':
                self.logger.info("Caught exception 'IncorrectState', handling the exception...")
                return {"Error": "IncorrectState"}
            if e.response['Error']['Code'] == 'DuplicateSubnetsInSameZone':
                self.logger.info("Caught exception 'DuplicateSubnetsInSameZone', handling the exception...")
                return {"Error": "DuplicateSubnetsInSameZone",
                        "Message": str(e)}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def remove_subnet_from_tgw_attachment(self, tgw_attachment_id, subnet_id):
        try:
            response = self.ec2_client.modify_transit_gateway_vpc_attachment(
                TransitGatewayAttachmentId=tgw_attachment_id,
                RemoveSubnetIds=[
                    subnet_id
                ]
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'IncorrectState':
                self.logger.info("Caught exception 'IncorrectState', handling the exception...")
                return {"Error": "IncorrectState"}
            elif e.response['Error']['Code'] == 'InsufficientSubnetsException':
                self.logger.info("Caught exception 'InsufficientSubnetsException', handling the exception...")
                return {"Error": "InsufficientSubnetsException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def create_tags(self, resource_id, key, value):
        try:
            response = self.ec2_client.create_tags(
                Resources=[
                    resource_id
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )

            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise