// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {Route, Routes} from "react-router-dom";
import Dashboard from "../../pages/dashboard";
import ActionItems from "../../pages/action-items";
import DashboardVersionHistory from "../../pages/version-history/index";


// This is the router for the app
// It is used to navigate between pages in the app


const AppRouter = <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/dashboard/:subnetId/:vpcId" element={<DashboardVersionHistory />} />
    <Route path="/action-items" element={<ActionItems />} />
</Routes>

export default AppRouter