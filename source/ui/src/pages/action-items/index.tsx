// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, {useContext, useEffect, useState} from "react";
import {Button, ButtonDropdown, SpaceBetween} from "@cloudscape-design/components";
import {API, graphqlOperation} from "aws-amplify";
import {getActionItemsFromTransitNetworkOrchestratorTables} from "../../graphql/queries";
import {CommonItem} from "../../types/CommonItem";
import {UserContext} from "../../components/context";
import {updateTransitNetworkOrchestratorTable} from "../../graphql/mutation";
import {ActionItemResultTable} from "../../components/table/ApplicationResultTable";
import {columnDefinitions} from "../../components/table/ColumnDefinitions";


const ActionItems = () => {
    const {setBreadCrumb, user} = useContext(UserContext)
    const [actionItems, setActionItems] = useState<CommonItem[]>([])
    const [selectedItems, setSelectedItems] = useState<CommonItem[]>([])
    const [isLoading, setLoading] = useState<boolean>(false)
    const [isActionVisible, setActionVisible] = useState<boolean>(false)

    const groups = user?.signInUserSession?.idToken?.payload["cognito:groups"] || ["none"];
    const loadActionItems = async () => {
        setLoading(true)
        const result = await API.graphql(
            graphqlOperation(getActionItemsFromTransitNetworkOrchestratorTables)
        )


        // @ts-ignore
        setActionItems(result['data']['getActionItemsFromTransitNetworkOrchestratorTables']['items'] as CommonItem[])

        setLoading(false)
    }

    const onSelectItems = (item: CommonItem[]) => {
        item.find((item) => item.Status === 'processing') ? setActionVisible(false) : setActionVisible(true)
        setSelectedItems(item)
    }

    const updateOperation = async (type: string) => {
        const currentTimeStamp = new Date();
        const UTCTimeStamp = currentTimeStamp.toISOString();

        const input = {
            SubnetId: selectedItems![0].SubnetId,
            Version: "latest",
            Status: "processing",
            UserId: user.username,
            GraphQLTimeStamp: UTCTimeStamp,
            AdminAction: type,
        };


        await API.graphql(
            graphqlOperation(updateTransitNetworkOrchestratorTable, {input})
        );

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