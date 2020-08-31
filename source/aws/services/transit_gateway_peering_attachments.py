###############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.    #
#                                                                             #
#  Licensed under the Apache License, Version 2.0 (the "License").            #
#  You may not use this file except in compliance                             #
#  with the License. A copy of the License is located at                      #
#                                                                             #
#      http://www.apache.org/licenses/LICENSE-2.0                             #
#                                                                             #
#  or in the "license" file accompanying this file. This file is distributed  #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES                                    #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the     #
#  specific language governing permissions                                    #
#  and limitations under the License.                                         #
###############################################################################

# !/bin/python
from botocore.exceptions import ClientError
from lib.decorator import try_except_retry
from aws.utils.boto3_session import Boto3Session


class TgwPeeringAttachmentAPIHandler(Boto3Session):
    def __init__(self, logger, region, **kwargs):
        self.logger = logger
        self.__service_name = 'ec2'
        self.region = region
        kwargs.update({'region': self.region})
        super().__init__(self.logger, self.__service_name, **kwargs)
        self.ec2_client = super().get_client()

    @try_except_retry()
    def describe_transit_gateway_peering_attachments(self,
                                                     tgw_id: str,
                                                     states: list) -> list:
        """
        Describe the tgw peering attachments for the tagged tgw id
        :param tgw_id: tgw id of the tagged transit gateway
        :param states: use the state to limit the returned response
        :return: list of transit gateway peering attachments
        """
        try:
            response = self.ec2_client\
                .describe_transit_gateway_peering_attachments(
                    Filters=[
                        {
                            'Name': 'transit-gateway-id',
                            'Values': [tgw_id]
                        },
                        {
                            'Name': 'state',
                            'Values': states
                        }
                    ]
                )

            transit_gateway_peering_attachments_list = response.get(
                'TransitGatewayPeeringAttachments', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                self.logger.info("Handling Next Token: {}".format(next_token))
                response = self.ec2_client\
                    .describe_transit_gateway_peering_attachments(
                        Filters=[
                            {
                                'Name': 'transit-gateway-id',
                                'Values': [tgw_id]
                            },
                            {
                                'Name': 'state',
                                'Values': states
                            }
                        ],
                        NextToken=next_token)
                self.logger.info("Extending TGW Peering Attachment List")
                transit_gateway_peering_attachments_list \
                    .extend(response.get('TransitGatewayPeeringAttachments',
                                         []))
                next_token = response.get('NextToken', None)

            return transit_gateway_peering_attachments_list
        except ClientError as error:
            self.logger.log_unhandled_exception(error)
            raise

    def create_transit_gateway_peering_attachment(self,
                                                  tgw_id: str,
                                                  peer_tgw_id: str,
                                                  peer_account_id,
                                                  peer_region) -> dict:
        """
            Create tgw peering attachment
        :param tgw_id: REQUIRED - transit gateway id of the local region
        :param peer_tgw_id: REQUIRED - id for peer transit gateway hosted in
        the peer region
        :param peer_account_id: REQUIRED - current account id
        :param peer_region: peer region where peer transit gateway is hosted
        :return: details for the tgw peering attachment
        """
        try:
            response = self.ec2_client\
                .create_transit_gateway_peering_attachment(
                    TransitGatewayId=tgw_id,
                    PeerTransitGatewayId=peer_tgw_id,
                    PeerAccountId=peer_account_id,
                    PeerRegion=peer_region,
                )
            return response.get('TransitGatewayPeeringAttachment')
        except ClientError as error:
            self.logger.log_unhandled_exception(error)
            raise

    def delete_transit_gateway_peering_attachment(self,
                                                  tgw_attach_id: str) -> str:
        """
            Delete tgw peering attachment
        :param tgw_attach_id: REQUIRED - transit gateway peering attachment id
        :return: current state of the peering attachment
        """
        try:
            response = self.ec2_client\
                .delete_transit_gateway_peering_attachment(
                    TransitGatewayAttachmentId=tgw_attach_id
                )
            return response.get('TransitGatewayPeeringAttachment').get('State')
        except ClientError as error:
            self.logger.log_unhandled_exception(error)
            raise

    def accept_transit_gateway_peering_attachment(self,
                                                  tgw_attach_id: str) -> str:
        """
            Accept tgw peering attachment
        :param tgw_attach_id: REQUIRED - transit gateway peering attachment id
        :return: current state of the peering attachment
        """
        try:
            response = self.ec2_client\
                .accept_transit_gateway_peering_attachment(
                    TransitGatewayAttachmentId=tgw_attach_id
                )
            return response.get('TransitGatewayPeeringAttachment').get('State')
        except ClientError as error:
            self.logger.log_unhandled_exception(error)
            raise

    def get_transit_gateway_peering_attachment_state(self,
                                                     tgw_attachment_id) -> list:
        """
        Describe the tgw peering attachments for the tagged tgw id
        :param tgw_attachment_id: tgw id of the tagged transit gateway
        :return: list of transit gateway peering attachments
        """
        try:
            response = self.ec2_client\
                .describe_transit_gateway_peering_attachments(
                 TransitGatewayAttachmentIds=[tgw_attachment_id])

            transit_gateway_peering_attachments_list = response.get(
                'TransitGatewayPeeringAttachments', [])
            next_token = response.get('NextToken', None)

            while next_token is not None:
                self.logger.info(
                    "Handling Next Token: {}".format(next_token))
                response = self.ec2_client \
                    .describe_transit_gateway_peering_attachments(
                      TransitGatewayAttachmentIds=[tgw_attachment_id],
                      NextToken=next_token)
                self.logger.info("Extending TGW Peering Attachment List")
                transit_gateway_peering_attachments_list \
                    .extend(response.get('TransitGatewayPeeringAttachments',
                                         []))
                next_token = response.get('NextToken', None)

            state = transit_gateway_peering_attachments_list[0].get('State')
            return state
        except ClientError as error:
            self.logger.log_unhandled_exception(error)
            raise
