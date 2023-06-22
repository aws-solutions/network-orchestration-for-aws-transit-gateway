// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {AppLayout, BreadcrumbGroup,} from "@cloudscape-design/components";
import CustomHeader from "../navigation/header";
import CustomSideNavigation from "../navigation/side-navigation";
import {BrowserRouter} from "react-router-dom";
import {useContext} from "react";
import {UserContext} from "../context";
import AppRouter from "../router";


// Base layout for all pages in the app

const CustomAppLayout = () => {
    const {breadCrumb} = useContext(UserContext)

    return (
        <div className={'full-layout'}>
            <CustomHeader/>
            <BrowserRouter>
                <AppLayout
                    headerSelector={"#header"}
                    navigation={<CustomSideNavigation/>}
                    toolsHide={true}
                    breadcrumbs={<BreadcrumbGroup items={breadCrumb}/>}
                    content={AppRouter}
                />
            </BrowserRouter>
        </div>

    )
}

export default CustomAppLayout