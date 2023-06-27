// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {useContext, useEffect, useState} from "react";
import {BreadcrumbGroupProps} from "@cloudscape-design/components";
import {useParams} from "react-router-dom";
import {UserContext} from "../../components/context";
import {VersionHistoryResultTable} from "../../components/table/ApplicationResultTable";
import {API, graphqlOperation} from "aws-amplify";
import {getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables} from "../../graphql/queries";
import { CommonItem } from "../../types/CommonItem";
import {columnDefinitions} from "../../components/table/ColumnDefinitions";


const DashboardVersionHistory = () => {

    const {setBreadCrumb} = useContext(UserContext)
    const {subnetId, vpcId} = useParams();
    const [versionHistory, setVersionHistory] = useState<CommonItem[]>([])
    const [isLoading,setLoading] = useState<boolean>(false)

    const getVersionHistory = async (subnetId?: string) => {
        setLoading(true)
        const result = await API.graphql(
            graphqlOperation(getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables, {
                    "filter": {"SubnetId": {"eq": subnetId}, "Version": {"ne": "latest"}}
                }
            )
        )
        // @ts-ignore
        setVersionHistory(result['data']['getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables']['items'] as CommonItem[])
        setLoading(false)
    }


    const breadcrumbs: BreadcrumbGroupProps.Item[] = [
        {text: 'Dashboard', href: '/dashboard'},
        {text: vpcId || "", href: '/dashboard/' + subnetId + '/' + vpcId},
    ];


    useEffect(() => {
        setBreadCrumb(breadcrumbs)
        getVersionHistory(subnetId).catch(e => console.error(e))
    }, [])


    return <VersionHistoryResultTable
        title={"Version History"}
        data={versionHistory}
        loading={isLoading}
        actions={<></>}
        columnDefinitions={columnDefinitions}
    />
}

export default DashboardVersionHistory