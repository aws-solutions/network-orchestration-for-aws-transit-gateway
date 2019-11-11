// eslint-disable
// this is an auto generated file. This will be overwritten

export const onUpdateTransitNetworkOrchestratorTable = `subscription OnUpdateTransitNetworkOrchestratorTable(
  $SubnetId: String
  $Version: String
) {
  onUpdateTransitNetworkOrchestratorTable(
    SubnetId: $SubnetId
    Version: $Version
  ) {
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
