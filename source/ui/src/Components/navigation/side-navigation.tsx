// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {SideNavigation, SideNavigationProps} from "@cloudscape-design/components";
import {useState} from "react";
import {useNavigate} from "react-router-dom";


const items: SideNavigationProps['items'] = [
    {type: 'link', text: 'Dashboard', href: '/'},
    {type: 'link', text: 'Action Items', href: '/action-items'},
];


// Custom side navigation component - this component is used in the main layout
// It is used to show the side navigation of the app - it is used to navigate between dashboard and action items page
const CustomSideNavigation = () => {

    const [currentPage, setCurrentPage] = useState<string>("/")
    const navigate = useNavigate();

    return (
        <SideNavigation
            onFollow={(event) => {
                if (!event.detail.external) {
                    event.preventDefault();
                    setCurrentPage(event.detail.href)
                    navigate(event.detail.href);
                }
            }}
            activeHref={currentPage}
            header={{href: '/', text: 'Network Orchestration for AWS Transit Network Gateway'}}
            items={items}
        />
    )
}

export default CustomSideNavigation