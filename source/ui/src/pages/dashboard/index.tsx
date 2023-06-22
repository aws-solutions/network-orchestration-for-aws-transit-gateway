// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {useContext, useEffect, useState} from "react";
import {Button} from "@cloudscape-design/components";
import {getDashboardItemsFromTransitNetworkOrchestratorTables} from "../../graphql/queries";

import {API, graphqlOperation} from 'aws-amplify';
import {UserContext} from "../../components/context";
import {DashboardResultTable } from "../../components/table/ApplicationResultTable";
import { useNavigate} from 'react-router-dom';
import { CommonItem } from "../../types/CommonItem";
import {columnDefinitions} from "../../components/table/ColumnDefinitions";
const Dashboard = () => {

    const {setBreadCrumb} = useContext(UserContext)
    const [isLoading,setLoading] = useState<boolean>(false)
    const navigate = useNavigate();

    const [dashboardItem, setDashboardItem] = useState<CommonItem[]>([])
    const getDashboardItems = async () => {
        setLoading(true)
        setDashboardItem([])
        const result = await API.graphql(
            graphqlOperation(getDashboardItemsFromTransitNetworkOrchestratorTables)
        )

        // @ts-ignore
        setDashboardItem(result['data']['getDashboardItemsFromTransitNetworkOrchestratorTables']['items'] as CommonItem[]);
        setLoading(false);
    }


    useEffect(() => {
        setBreadCrumb([])
        getDashboardItems().catch((e) => {
            console.log(e)
        })
    }, [])

    const onRowClick = (item: CommonItem) => {
        // @ts-ignore
        navigate(`/dashboard/${item.SubnetId}/${item.VpcId}`)
    }


    return <DashboardResultTable
            className={"clickable-table"}
            title={"Dashboard"}
            data={dashboardItem}
            loading={isLoading}
            actions={
                <Button iconName="refresh" onClick={getDashboardItems}>
                    Refresh
                </Button>
            }
            columnDefinitions={columnDefinitions}
            onRowClick={(item) => {
            console.log(item)
                onRowClick(item as CommonItem)
            }}
        />
}

export default Dashboard