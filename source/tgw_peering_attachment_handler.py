################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.     #
#                                                                              #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may     #
#  not use this file except in compliance  with the License. A copy of the     #
#  License is located at                                                       #
#      http://www.apache.org/licenses/LICENSE-2.0                              #
#                                                                              #
#  or in the "license" file accompanying this file. This file is distributed   #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express  #
#  or implied. See the License for the specific language governing permissions #
#  and limitations under the License.                                          #
################################################################################
# !/bin/python

from lib.logger import Logger
from os import environ
from lib.string_manipulation import get_delimiter
import aws.services.transit_gateway_peering_attachments as tgw_pa
from lib.metrics import Metrics

# initialise logger
DEFAULT_LOG_LEVEL = 'info'
LOG_LEVEL = environ.get('LOG_LEVEL') if environ.get('LOG_LEVEL') is not None \
    else DEFAULT_LOG_LEVEL
logger = Logger(loglevel=LOG_LEVEL)


class TgwTagEventModifier:
    def __init__(self, event):
        self.logger = logger
        self.event = event
        self.tag_details = self.event.get('detail')
        self.peering_tag = self.reduce_tag_list_to_match_prefix()

    def reduce_tag_list_to_match_prefix(self) -> str:
        """
        Handles a tagging event if user adds multiple tags to the transit
        gateway and one of them may match the defined tag prefix
        :return: either tag key that matched the prefix or inapplicable_tag
        """
        inapplicable_tag = 'InapplicableTag-Skipping-Tgw-Peering-Workflow'
        reduced_list = [tag for tag in self.tag_details.get(
            'changed-tag-keys') if tag.startswith(
            environ.get('TGW_PEERING_TAG_PREFIX'))]
        if reduced_list:
            if len(reduced_list) > 1:
                # print and add note in the event in if there are more than
                # two tag keys that match the prefix.
                error = f"STNO Error: Please delete and add following tag " \
                        f"keys individually: {reduced_list}"
                raise KeyError(error)
            self.event.update({"PeeringTag": reduced_list[0]})
            peering_tag = self.strip_white_spaces(reduced_list[0])
            return peering_tag
        else:
            return inapplicable_tag

    def is_valid_tagging_event(self) -> bool:
        """
        verify if the event is from a tag change on a resource type of
        transit gateway. Raises exception if the event is not from the
        correct resource type.
       :return:
       """
        logger.info("Validate transit gateway tagging event")
        is_valid_peering_tag = True if self.peering_tag.startswith(
            environ.get('TGW_PEERING_TAG_PREFIX')) else False
        # if it's valid tgw event but doesn't have defined tag prefix
        if is_valid_peering_tag:
            self.event.update({"IsTgwPeeringTagEvent": "Yes"})
        else:
            message = (f"Skipping state machine workflow - the tagging "
                       f"event is not related to the user defined peering tag "
                       f"prefix: {environ.get('TGW_PEERING_TAG_PREFIX')}")
            logger.info(message)
            self.event.update({"Message": message})
            self.event.update({"IsTgwPeeringTagEvent": "No"})
        return is_valid_peering_tag

    def add_request_type(self) -> None:
        """
        check if this is a create or delete tag event
        :return: event
        """
        if self.event.get('RequestType') is None:
            if self.peering_tag in self.tag_details.get('tags'):
                self.event.update({"RequestType": "Create"})
            elif self.peering_tag not in self.tag_details.get('tags'):
                self.event.update({"RequestType": "Delete"})

    def update_event_with_tgw_peer_data(self) -> None:
        """
        parse and move nested values to the top level dictionary level keys
        skips event update if they already exist
        """
        peering_keys = ["TgwId", "PeerTgwId", "PeerRegion", "PeerAccountId"]
        # check for existing peering keys to skip redundant event update
        if not all(key in self.event for key in peering_keys):
            peering_data = {
                "TgwId": self._get_transit_gateway_id_from_arn(),
                "PeerTgwId": self._get_peer_transit_gateway_id(),
                "PeerRegion": self._get_peer_region(),
                "PeerAccountId": self.event.get('account'),  # same account
             }
            self.event.update(peering_data)

    def _get_transit_gateway_id_from_arn(self) -> str:
        """
        parse the transit gateway arn in the tagging event to get the requesting
        transit gateway id
        :return: transit gateway id from the local region
        """
        arn = self.event.get('resources')[0]
        return arn.split('/')[1]

    def _get_peer_transit_gateway_id(self) -> str:
        """
        finds the changed tag key in the transit gateway tags and returns the
        value. As per the tagging scheme this value must be the peering tgw id
        transit gateway id
        :return: peer transit gateway id
        """
        peer_tgw_id = self.tag_details.get('tags').get(self.peering_tag, 'None')
        stripped_peer_tgw_id = self.strip_white_spaces(peer_tgw_id)
        return stripped_peer_tgw_id

    def _get_peer_region(self) -> str:
        """
        parse changed tag key to get the peer region name
        :return: parsed value of peer region from the peering tag
        """
        peer_region = self.peering_tag.split(get_delimiter(environ.get(
            'TGW_PEERING_TAG_DELIMITER')))[1]
        stripped_peer_region = self.strip_white_spaces(peer_region)
        return stripped_peer_region

    @staticmethod
    def strip_white_spaces(value):
        stripped_value = value.strip() if value is not None else value
        return stripped_value


class TgwTagEventHandler:
    def __init__(self, event):
        self.logger = logger
        self.event = event
        self.tag_details = self.event.get('detail')
        self.peering_tag = self.event.get('PeeringTag')
        self.local_region = environ.get('AWS_REGION')
        self.peer_region = event.get('PeerRegion')
        self.local_tgw_id = environ.get('TGW_ID')
        self.peer_tgw_id = event.get('PeerTgwId')
        self.peer_account_id = event.get('PeerAccountId')
        self.tgw_peering_client = tgw_pa.TgwPeeringAttachmentAPIHandler(
            logger,
            self.local_region)

    def get_processed_tagging_event(self):
        event_processor = TgwTagEventModifier(self.event)
        if event_processor.is_valid_tagging_event():
            event_processor.add_request_type()
            event_processor.update_event_with_tgw_peer_data()
        return event_processor.event

    def get_transit_gateway_peering_attachment_id(self) -> dict:
        """
        update event with tgw peering attachment id if exists else update event
        with flags to create a new tgw peering attachment
        :return: event
        """
        states = ['available', 'pending', 'modifying',
                  'initiating', 'pendingAcceptance']
        # avoid listing 'deleted' peer attachments for delete request types
        if self.event.get('RequestType') == 'Create':
            states.append('deleted')
        peering_attachment_not_found = {
            'TgwPeeringAttachmentExist': 'No',
            'TgwPeeringAttachmentState': 'does-not-exist'
        }
        list_of_tgw_attachments = self.tgw_peering_client \
            .describe_transit_gateway_peering_attachments(self.local_tgw_id,
                                                          states)
        self.logger.info(list_of_tgw_attachments)

        if list_of_tgw_attachments:
            self.tgw_peering_attachment_id_finder(list_of_tgw_attachments,
                                                  peering_attachment_not_found)
        else:
            self.event.update(peering_attachment_not_found)
        return self.event

    def tgw_peering_attachment_id_finder(self, list_of_tgw_attachments,
                                         peering_attachment_not_found):
        remote_tgw_and_tgw_attach_id_map = {}
        peer_attachment_state_map = {}
        for tgw_peering_attachment in list_of_tgw_attachments:
            requester_region = tgw_peering_attachment.get(
                'RequesterTgwInfo').get('Region')
            accepter_region = tgw_peering_attachment.get(
                'AccepterTgwInfo').get('Region')
            tgw_peering_attachment_id = tgw_peering_attachment.get(
                'TransitGatewayAttachmentId')
            remote_tgw_peer_id = tgw_peering_attachment.get(
                'AccepterTgwInfo').get('TransitGatewayId')
            tgw_peer_attachment_state = tgw_peering_attachment.get('State')

            # build list of tgw id and peering attachment map if match the
            # local and remote regions for the peer
            if requester_region == self.local_region and \
                    accepter_region == self.peer_region:
                remote_tgw_and_tgw_attach_id_map.update(
                    {remote_tgw_peer_id: tgw_peering_attachment_id})
                peer_attachment_state_map.update(
                    {tgw_peering_attachment_id: tgw_peer_attachment_state})
        self.logger.info(f"TGW ID:TGW Attach ID Reduced Map:"
                         f"{remote_tgw_and_tgw_attach_id_map}")
        self.logger.info(f"Attachment ID: State Map: "
                         f"{peer_attachment_state_map}")
        final_attachment_id = self.get_attachment_id(
            remote_tgw_and_tgw_attach_id_map)
        self.logger.info(f"Attachment ID: {final_attachment_id}")
        if final_attachment_id is None:
            self.event.update(peering_attachment_not_found)
        else:
            self.event.update({'TgwPeeringAttachmentExist': 'Yes'})
            self.event.update({'TgwPeeringAttachmentId': final_attachment_id})
            self.event.update(
                {'TgwPeeringAttachmentState': peer_attachment_state_map.get(
                    final_attachment_id)})

    def get_attachment_id(self, remote_tgw_and_tgw_attach_id_map):
        # get attachment id for attachment deletion workflow
        if self.peer_tgw_id == 'None':
            # build list of tgw id peering in the same region
            same_region_tag = "%s%s%s" % (environ.get('TGW_PEERING_TAG_PREFIX'),
                                          get_delimiter(environ.get(
                                              'TGW_PEERING_TAG_DELIMITER')),
                                          self.event.get('PeerRegion'))
            tags = self.tag_details.get('tags')
            self.logger.info(f"Same Region Tag: {same_region_tag}")
            self.logger.info(f"Tags in Event: {tags}")
            tgw_in_tags = [value for key, value in tags.items() if
                           key.startswith(same_region_tag)]
            self.logger.info(f"Peer Tgw IDs in the Tag: {tgw_in_tags}")
            # remove tgw and attachment map for existing tags
            for tgw in tgw_in_tags:
                remote_tgw_and_tgw_attach_id_map.pop(tgw, None)
            self.logger.info(
                f"TGW ID:TGW Attach ID Reduced Map: "
                f"{remote_tgw_and_tgw_attach_id_map}")
            # After popping all the keys, we will always be left with just one
            # key
            final_attachment_id = list(
                remote_tgw_and_tgw_attach_id_map.values())[0]
        else:  # get attachment id for attachment creation workflow
            final_attachment_id = remote_tgw_and_tgw_attach_id_map.get(
                self.peer_tgw_id)
        return final_attachment_id

    def create_transit_gateway_peering_attachment(self) -> dict:
        """
        updates the event with the transit gateway peering attachment id and
        it's current state.
        :return:
        """
        if self.event.get('TgwPeeringAttachmentExist') == 'No' or (
                self.event.get('TgwPeeringAttachmentExist') == 'Yes' and
                self.event.get('TgwPeeringAttachmentState') == 'deleted'):
            response = self.tgw_peering_client\
                .create_transit_gateway_peering_attachment(self.local_tgw_id,
                                                           self.peer_tgw_id,
                                                           self.peer_account_id,
                                                           self.peer_region)
            tgw_peering_id = response.get('TransitGatewayAttachmentId')
            tgw_peering_state = response.get('State')
            self.event.update({'TgwPeeringAttachmentId': tgw_peering_id})
            self.event.update({'TgwPeeringAttachmentState': tgw_peering_state})
        return self.event

    def accept_transit_gateway_peering_attachment(self) -> dict:
        if self.event.get('TgwPeeringAttachmentState') == 'pendingAcceptance':
            tgw_peering_remote_client = tgw_pa.TgwPeeringAttachmentAPIHandler(
                self.logger,
                self.peer_region)
            tgw_peering_state = tgw_peering_remote_client\
                .accept_transit_gateway_peering_attachment(self.event.get(
                 'TgwPeeringAttachmentId'))
            self.event.update({'TgwPeeringAttachmentState': tgw_peering_state})
        return self.event

    def get_transit_gateway_peering_attachment_state(self) -> dict:
        tgw_peering_state = self.tgw_peering_client\
            .get_transit_gateway_peering_attachment_state(
             self.event.get('TgwPeeringAttachmentId'))
        self.event.update({'TgwPeeringAttachmentState': tgw_peering_state})

        # send metrics in the last stage of the state machine.
        self.send_tgw_peering_anonymous_data()

        return self.event

    def delete_transit_gateway_peering_attachment(self) -> dict:
        if self.event.get('TgwPeeringAttachmentExist') == 'Yes' and \
                self.event.get('TgwPeeringAttachmentState') == 'available':
            tgw_peering_state = self.tgw_peering_client\
                .delete_transit_gateway_peering_attachment(
                 self.event.get('TgwPeeringAttachmentId'))
            self.event.update({'TgwPeeringAttachmentState': tgw_peering_state})

        return self.event

    def send_tgw_peering_anonymous_data(self) -> any:
        final_states = ['available', 'deleted']
        if self.event.get('TgwPeeringAttachmentState') in final_states:
            send = Metrics(self.logger)
            data = {
                "TgwPeeringState": self.event.get('TgwPeeringAttachmentState'),
                "Region": environ.get('AWS_REGION'),
                "PeerRegion": self.event.get('PeerRegion'),
                "RequestType": self.event.get('RequestType'),
                "TagEventSource": "TransitGateway",
                "SolutionVersion": environ.get('SOLUTION_VERSION')
            }
            return send.metrics(data)
        else:
            return None


def lambda_handler(event, context):
    """
    :param event: tgw tagging event (initial)
    :param context: lambda context - defined by the AWS Lambda service
    :return: event returned by the method on the handler class
    """
    # Lambda handler function
    try:
        method_name = event.get('params').get('MethodName')
        class_object = TgwTagEventHandler(event)

        logger.info(f"Lambda Handler Event - executing method: {method_name}")
        logger.info(event)
        logger.debug(context)

        try:
            method = getattr(class_object, method_name)
            return method()
        except AttributeError:
            raise NotImplementedError(f"{method_name} is not a valid method.")
    except BaseException as error:
        logger.exception("Unable to process the tagging event")
        raise error
