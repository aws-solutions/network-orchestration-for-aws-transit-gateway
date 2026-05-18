// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, {useContext, useEffect, useRef, useState} from "react";
import {Button, ButtonDropdown, SpaceBetween} from "@cloudscape-design/components";
import {generateClient} from "aws-amplify/api";
import {getActionItemsFromTransitNetworkOrchestratorTables, getDashboardItemsFromTransitNetworkOrchestratorTables} from "../../graphql/queries";
import {CommonItem} from "../../types/CommonItem";
import {UserContext} from "../../components/context";
import {updateTransitNetworkOrchestratorTable} from "../../graphql/mutation";
import {ActionItemResultTable} from "../../components/table/ApplicationResultTable";
import {columnDefinitions} from "../../components/table/ColumnDefinitions";

const client = generateClient();


const ActionItems = () => {
    const {setBreadCrumb, user} = useContext(UserContext)
    const [actionItems, setActionItems] = useState<CommonItem[]>([])
    const [selectedItems, setSelectedItems] = useState<CommonItem[]>([])
    const [isLoading, setLoading] = useState<boolean>(false)
    const [isActionVisible, setActionVisible] = useState<boolean>(false)
    const actionItemsRef = useRef<CommonItem[]>([])
    const dashboardItemsRef = useRef<CommonItem[]>([])

    const groups = user?.groups || [];
    const loadActionItems = async () => {
        setLoading(true)
        const [actionResult, dashboardResult] = await Promise.all([
            client.graphql({ query: getActionItemsFromTransitNetworkOrchestratorTables }),
            client.graphql({ query: getDashboardItemsFromTransitNetworkOrchestratorTables })
        ])

        // @ts-ignore
        const items = actionResult['data']['getActionItemsFromTransitNetworkOrchestratorTables']['items'] as CommonItem[]
        setActionItems(items)
        actionItemsRef.current = items
        // @ts-ignore
        dashboardItemsRef.current = dashboardResult['data']['getDashboardItemsFromTransitNetworkOrchestratorTables']['items'] as CommonItem[]

        setLoading(false)
    }

    const onSelectItems = (item: CommonItem[]) => {
        const hasProcessing = item.some((i) => i.Status === 'processing');
        const isVpcWithoutSubnet = item.some((i) =>
            i.TagEventSource === 'vpc' &&
            !actionItemsRef.current.some((ai) => ai.TagEventSource === 'subnet' && ai.VpcId === i.VpcId) &&
            !dashboardItemsRef.current.some((di) => di.TagEventSource === 'subnet' && di.VpcId === i.VpcId)
        );
        setActionVisible(!hasProcessing && !isVpcWithoutSubnet);
        setSelectedItems(item)
    }

    const updateOperation = async (type: string) => {
        if (!selectedItems || selectedItems.length === 0) {
            console.error('No items selected for update operation');
            return;
        }
        if (!user) {
            console.error('No authenticated user');
            return;
        }
        const currentTimeStamp = new Date();
        const UTCTimeStamp = currentTimeStamp.toISOString();

        const input = {
            SubnetId: selectedItems[0].SubnetId,
            Version: "latest",
            Status: "processing",
            UserId: user.username,
            GraphQLTimeStamp: UTCTimeStamp,
            AdminAction: type,
        };

        await client.graphql({
            query: updateTransitNetworkOrchestratorTable,
            variables: {input}
        });

        loadActionItems().catch((error) => {
            console.log(error)
        })
    }

    useEffect(() => {
        setBreadCrumb([])
        loadActionItems().catch((error) => {
            console.log(error)
        })
    }, [setBreadCrumb])

    return <ActionItemResultTable
        title={"Action Items"}
        data={actionItems}
        loading={isLoading}
        actions={
            <SpaceBetween size={"s"} direction="horizontal">
                {isActionVisible && groups.indexOf("AdminGroup") !== -1 &&
                    <ButtonDropdown
                        onItemClick={(e) => {
                            if (e.detail.id === "approve") {
                                updateOperation("accept").catch((_) => {
                                })
                            }

                            if (e.detail.id === "reject") {
                                updateOperation("reject").then((_) => {
                                })
                            }
                        }}
                        items={[
                            {text: "Approve", id: "approve", disabled: false},
                            {text: "Reject", id: "reject", disabled: false},
                        ]}
                    >
                        Action
                    </ButtonDropdown>
                }
                <Button iconName={"refresh"} onClick={() => loadActionItems()}>Refresh</Button>
            </SpaceBetween>
        }
        columnDefinitions={columnDefinitions}
        selectedItems={selectedItems as [any]}
        onItemSelected={onSelectItems}
    />


}

export default ActionItems
