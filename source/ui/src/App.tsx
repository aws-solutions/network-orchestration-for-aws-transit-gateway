// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {applyDensity, Density} from "@cloudscape-design/global-styles";
import {useContext} from "react";
import {UserContext} from "./components/context";
import {signInWithRedirect} from "aws-amplify/auth";
import CustomAppLayout from "./components/layout";
import {Spinner} from "@cloudscape-design/components";

applyDensity(Density.Comfortable)

function App() {
    const {user, signingOut} = useContext(UserContext)

    if (!user && !signingOut) {
        signInWithRedirect().catch((error) => {
            console.error(error);
        })
    }

    if (!user)
        return <>
            <Spinner></Spinner>
            <div>{signingOut ? "Signing out..." : "Redirecting to login..."}</div>
        </>

    else {
        return (
            <CustomAppLayout/>
        )
    }
}

export default App
