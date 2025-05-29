// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
// eslint-disable
// this is an auto generated file. This will be overwritten

export const getActionItemsFromTransitNetworkOrchestratorTables: string = `query GetActionItemsFromTransitNetworkOrchestratorTables(
    $filter: TableTransitNetworkOrchestratorTableDashboardActionItemsFilterInput
    $limit: Int
    $nextToken: String
  ) {
    getActionItemsFromTransitNetworkOrchestratorTables(
      filter: $filter
      limit: $limit
      nextToken: $nextToken
    ) {
      items {
        AWSSpokeAccountId
        Action
        AdminAction
        AvailabilityZone
        Comment
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
      nextToken
    }
  }
  `;
export const getDashboardItemsFromTransitNetworkOrchestratorTables: string = `query getDashboardItemsFromTransitNetworkOrchestratorTables(
    $filter: TableTransitNetworkOrchestratorTableDashboardActionItemsFilterInput
    $limit: Int
    $nextToken: String
  ) {
    getDashboardItemsFromTransitNetworkOrchestratorTables(
      filter: $filter
      limit: $limit
      nextToken: $nextToken
    ) {
      items {
        AWSSpokeAccountId
        Action
        AdminAction
        AvailabilityZone
        Comment
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
      nextToken
    }
  }
  `;
export const getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables = `query GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables(
    $filter: TableTransitNetworkOrchestratorTableVersionHistoryFilterInput
    $limit: Int
    $nextToken: String
  ) {
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables(
      filter: $filter
      limit: $limit
      nextToken: $nextToken
    ) {
      items {
        AWSSpokeAccountId
        Action
        AdminAction
        AvailabilityZone
        Comment
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
      nextToken
    }
  }
  `;
  