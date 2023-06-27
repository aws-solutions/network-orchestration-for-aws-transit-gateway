// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {applyDensity, Density} from "@cloudscape-design/global-styles";
import {useContext} from "react";
import {UserContext} from "./components/context";
import Auth from "@aws-amplify/auth";
import CustomAppLayout from "./components/layout";
import {Spinner} from "@cloudscape-design/components";

applyDensity(Density.Comfortable)

function App() {
    const {user} = useContext(UserContext)

    if (!user) {
        Auth.federatedSignIn().catch((error) => {
            console.error(error);
        })
    }


    if (!user)
        return <>
            <Spinner></Spinner>
            <div>Redirecting to login...</div>
        </>

    else {
        return (
            <CustomAppLayout/>
        )
    }
}

export default App
