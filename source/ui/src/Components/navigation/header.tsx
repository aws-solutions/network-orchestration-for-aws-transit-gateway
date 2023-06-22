// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { TopNavigation, ButtonDropdownProps } from "@cloudscape-design/components";
import { useContext } from "react";
import { UserContext } from "../context";
import Auth from '@aws-amplify/auth';


const DOC_URL = "https://aws.amazon.com/solutions/implementations/network-orchestration-aws-transit-gateway/"

// Custom header component
// This component is used in the main layout to show the header of the app
const CustomHeader = () => {

    const { user } = useContext(UserContext);

    const menuItemClick = async (props: CustomEvent<ButtonDropdownProps.ItemClickDetails>) => {
        const id = props.detail.id;

        if(id === 'signout') {
            Auth.signOut().catch((error: Error) => {
                console.error(error)
            })
        }
    }

    return <TopNavigation
        identity={{
            title: '',
            href: '/',
        }}
        i18nStrings={{
            overflowMenuTriggerText: 'More',
            overflowMenuTitleText: 'All',
        }}
        utilities={[
            {
                type: "menu-dropdown",
                text: user != null ? user.username : "Unknown User",
                iconName: "user-profile",
                items: [
                    {
                        id: "document", text: "Documentation", href: DOC_URL,
                        external: true,
                        externalIconAriaLabel: " (opens in new tab)"
                    },
                    { id: "signout", text: "Sign out" }
                ],
                onItemClick: menuItemClick
            }
        ]}
    />
}

export default CustomHeader