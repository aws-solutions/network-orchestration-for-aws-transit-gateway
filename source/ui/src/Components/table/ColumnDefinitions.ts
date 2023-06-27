import {TableProps} from "@cloudscape-design/components";
import {CommonItem} from "../../types/CommonItem";

export const columnDefinitions: Array<TableProps.ColumnDefinition<CommonItem>> = [
        {
            header: "Request Time",
            cell: ({RequestTimeStamp}) => RequestTimeStamp,
            sortingField: 'RequestTimeStamp',
            minWidth: 200,
        },
        {
            header: "Tag Event Source",
            cell: ({TagEventSource}) => TagEventSource,
            sortingField: 'TagEventSource',
            minWidth: 200,
        },
        {
            header: "Spoke Account",
            cell: ({AWSSpokeAccountId}) => AWSSpokeAccountId,
            sortingField: 'AWSSpokeAccountId',
            minWidth: 180,
        },
        {
            header: 'VPC Id',
            cell: ({VpcId}) => VpcId,
            sortingField: 'VpcId',
            minWidth: 205,
        },
        {
            header: 'VPC CIDR',
            cell: ({VpcCidr}) => VpcCidr,
            sortingField: 'VpcCidr',
            minWidth: 150,
        },
        {
            header: "Subnet Id",
            cell: ({SubnetId}) => SubnetId,
            sortingField: 'SubnetId',
            minWidth: 230,
        },
        {
            header: "Availability Zone",
            cell: ({AvailabilityZone}) => AvailabilityZone,
            sortingField: 'AvailabilityZone',
            minWidth: 180,
        },
        {
            header: 'Status',
            cell: ({Status}) => Status,
            sortingField: 'Status',
            minWidth: 130,
        },
        {
            header: 'Comment',
            cell: ({Comment}) => Comment,
            sortingField: 'Comment',
            minWidth: 200,
        },
        {
            header: "Association Route Table",
            cell: ({AssociationRouteTable}) => AssociationRouteTable,
            sortingField: 'AssociationRouteTable',
            minWidth: 220,
        },
        {
            header: "Propagation Route Table",
            cell: ({PropagationRouteTablesString}) => PropagationRouteTablesString,
            sortingField: 'PropagationRouteTablesString',
            minWidth: 230,
        },
        {
            header: "Response Time",
            cell: ({ResponseTimeStamp}) => ResponseTimeStamp,
            sortingField: 'ResponseTimeStamp',
            minWidth: 220,
        },
        {
            header: "Transit Gateway Id",
            cell: ({TgwId}) => TgwId,
            sortingField: 'TgwId',
            minWidth: 220,
        },
    ];