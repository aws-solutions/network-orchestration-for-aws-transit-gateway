// eslint-disable
// this is an auto generated file. This will be overwritten

export const getActionItemsFromTransitNetworkOrchestratorTables = `query GetActionItemsFromTransitNetworkOrchestratorTables(
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
export const getDashboarItemsFromTransitNetworkOrchestratorTables = `query GetDashboarItemsFromTransitNetworkOrchestratorTables(
  $filter: TableTransitNetworkOrchestratorTableDashboardActionItemsFilterInput
  $limit: Int
  $nextToken: String
) {
  getDashboarItemsFromTransitNetworkOrchestratorTables(
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
export const getDashboarItemsForStatusFromTransitNetworkOrchestratorTables = `query GetDashboarItemsForStatusFromTransitNetworkOrchestratorTables(
  $filter: TableTransitNetworkOrchestratorTableDashboardActionItemsFilterInput
  $limit: Int
  $nextToken: String
) {
  getDashboarItemsForStatusFromTransitNetworkOrchestratorTables(
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
