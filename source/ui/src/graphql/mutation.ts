// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
export const updateTransitNetworkOrchestratorTable : string = `mutation UpdateTransitNetworkOrchestratorTable(
    $input: UpdateTransitNetworkOrchestratorTableInput!
  ) {
    updateTransitNetworkOrchestratorTable(input: $input) {
      AWSSpokeAccountId
      Action
      AdminAction
      AvailabilityZone
      Comment
      GraphQLTimeStamp
      RequestTimeStamp
      ResponseTimeStamp
      Status
      SubnetId
      AssociationRouteTable
      PropagationRouteTablesString
      TagEventSource
      TgwId
      TimeToLive
      UserId
      Version
      VpcCidr
      VpcId
    }
  }
  `;
  