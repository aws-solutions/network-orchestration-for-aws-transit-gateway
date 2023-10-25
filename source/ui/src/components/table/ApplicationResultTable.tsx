// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {useCollection} from "@cloudscape-design/collection-hooks";
import {Box, TableProps, TextFilter} from "@cloudscape-design/components";
import Pagination from "@cloudscape-design/components/pagination";
import {ReactElement, useState} from "react";
import Table from "@cloudscape-design/components/table";
import Header from "@cloudscape-design/components/header";
import CollectionPreferences from "@cloudscape-design/components/collection-preferences";
import {SortingState} from "@cloudscape-design/collection-hooks/dist/mjs/interfaces";

export type TableState = {
    header: string,
    start: number,
    itemsPerPage: number
}

export const pageSizePreference = {
    title: "Items per page",
    options: [
        {
            value: 10,
            label: "10 items"
        },
        {
            value: 20,
            label: "20 items"
        },
        {
            value: 50,
            label: "50 items"
        }
    ]
};

export const createPagination = (
    tableState: TableState,
    setTableState: (t: TableState) => void,
    items: readonly any[]
) =>
    <Pagination
        ariaLabels={{
            nextPageLabel: "Next page",
            previousPageLabel: "Previous page",
            pageLabel: (pageNumber) => `Page ${pageNumber}`
        }}
        currentPageIndex={tableState.start}
        pagesCount={Math.ceil(items.length / tableState.itemsPerPage)}
        onChange={(e) => {
            setTableState({
                ...tableState,
                start: e.detail.currentPageIndex
            });
        }}
        onNextPageClick={(e) => {
            setTableState({
                ...tableState,
                start: e.detail.requestedPageIndex
            });
        }}
        onPreviousPageClick={(e) => {
            setTableState({
                ...tableState,
                start: e.detail.requestedPageIndex
            });
        }}
    />;


type AttachmentsResultTableProps = {
    className?: string,
    title: string,
    data: any[],
    loading: boolean,
    sorting: { defaultState?: SortingState<any> },
    headerVariant: any,
    tableVariant: TableProps.Variant,
    actions: React.ReactElement<any, string | React.JSXElementConstructor<any>>,
    columnDefinitions: Array<TableProps.ColumnDefinition<any>>

    onItemSelected?: (item: any) => void,

    selectedItems?: [any],

    selectionMode?: TableProps.SelectionType,

    onRowClick?: (item: any) => void
};

export function AttachmentsResultTable(props: AttachmentsResultTableProps) {
    const {
        className,
        title,
        data,
        loading,
        sorting,
        headerVariant,
        tableVariant,
        actions,
        columnDefinitions
    } = props;

    const [tableState, setTableState] = useState<TableState>({
        header: title,
        start: 1,
        itemsPerPage: 20
    });

    const {
        items,
        filterProps,
        collectionProps
    } = useCollection(data, {
        filtering: {
            empty: (
                <Box textAlign='center' color='inherit'>
                    <b>No resources</b>
                    <Box padding={{bottom: 's'}} variant='p' color='inherit'>
                        No resources to display.
                    </Box>
                </Box>
            ),
            noMatch: (
                <Box textAlign='center' color='inherit'>
                    <b>No match</b>
                    <Box padding={{bottom: 's'}} variant='p' color='inherit'>
                        No resources matched.
                    </Box>
                </Box>
            ),
        },
        sorting: sorting,
    });

    const pagination = createPagination(tableState, setTableState, items);

    const preferences = <CollectionPreferences
        title="Preferences"
        pageSizePreference={pageSizePreference}
        preferences={{
            pageSize: tableState.itemsPerPage
        }}
        onConfirm={(e) => {
            setTableState({
                ...tableState,
                itemsPerPage: e.detail.pageSize || 20
            });
        }}
        confirmLabel="Confirm"
        cancelLabel="Cancel"
    />;

    return <Table
        {...collectionProps}
        header={<Header variant={headerVariant} actions={actions}
                        counter={`(${items.length})`}>{tableState.header}</Header>}
        variant={tableVariant}
        loading={loading}
        onSelectionChange={(e) => {
            if (props.onItemSelected) {
                props.onItemSelected(e.detail.selectedItems);
            }
        }}
        onRowClick={(e) => {
            if (props.onRowClick) {
                props.onRowClick(e.detail.item);
            }
        }}
        selectedItems={props.selectedItems ? props.selectedItems : []}
        loadingText={'Loading resources'}
        className={className || ""}
        stickyHeader={true}
        selectionType={props.selectionMode ? props.selectionMode : undefined}
        resizableColumns={true}
        filter={
            <TextFilter {...filterProps} filteringPlaceholder="Find resources"/>
        }
        preferences={
            preferences
        }
        pagination={pagination}
        columnDefinitions={columnDefinitions}
        items={items.slice(
            (tableState.start - 1) * tableState.itemsPerPage,
            tableState.start * tableState.itemsPerPage
        )}
        wrapLines={true}
    ></Table>
}

export function DashboardResultTable({className, title, data, loading, actions, columnDefinitions, defaultSorting, onRowClick}: {
    className: string,
    title: string,
    data: any[],
    loading: boolean,
    actions: ReactElement,
    columnDefinitions: Array<TableProps.ColumnDefinition<any>>,
    defaultSorting?: TableProps.SortingState<any>,
    onRowClick?: (item: any) => void
}) {

    const tableVariant = "full-page";
    const headerVariant = "awsui-h1-sticky";
    const sorting = {
        defaultState: defaultSorting || {
            sortingColumn: {sortingField: 'RequestTimeStamp'},
            isDescending: true
        }
    };
    return AttachmentsResultTable({
        className,
        title,
        data,
        loading,
        sorting,
        headerVariant,
        tableVariant,
        actions,
        columnDefinitions,
        onRowClick
    });
}

export function ActionItemResultTable({title, data, loading, actions, columnDefinitions, onItemSelected,selectedItems}: {
    title: string,
    data: any[],
    loading: boolean,
    actions: ReactElement,
    columnDefinitions: Array<TableProps.ColumnDefinition<any>>,
    onItemSelected: (item: any) => void,
    selectedItems?: [any]
}) {

    const tableVariant = "full-page";
    const headerVariant = "awsui-h1-sticky";
    const sorting = {
        defaultState: {
            sortingColumn: {sortingField: 'RequestTimeStamp'},
            isDescending: true
        }
    };
    return AttachmentsResultTable({
        title,
        data,
        loading,
        sorting,
        headerVariant,
        tableVariant,
        actions,
        columnDefinitions,
        onItemSelected,
        selectedItems,
        selectionMode: 'single'
    });
}


export function VersionHistoryResultTable({title, data, loading, actions, columnDefinitions, defaultSorting}: {
    title: string,
    data: any[],
    loading: boolean,
    actions: ReactElement,
    columnDefinitions: Array<TableProps.ColumnDefinition<any>>,
    defaultSorting?: TableProps.SortingState<any>
}) {

    const tableVariant = "full-page";
    const headerVariant = "awsui-h1-sticky";
    const sorting = {
        defaultState: defaultSorting || {
            sortingColumn: {sortingField: 'RequestTimeStamp'},
            isDescending: true
        }
    };
    return AttachmentsResultTable({
        title,
        data,
        loading,
        sorting,
        headerVariant,
        tableVariant,
        actions,
        columnDefinitions
    });
}