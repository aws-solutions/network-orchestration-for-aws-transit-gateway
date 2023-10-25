// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { createContext, useEffect, useState } from "react";
import { Auth } from "@aws-amplify/auth";
import Amplify, { Hub } from "@aws-amplify/core";
import {BreadcrumbGroupProps} from "@cloudscape-design/components";

// stno_config object is assembled by custom_resource_helper into stno_config.js and loaded by index.html
// contains aws_appsync and cognito auth configuration
// @ts-ignore
Amplify.configure(window.stno_config);

type UserContextType = {
    user: any;
    setUser: (user: any) => void;

    breadCrumb: BreadcrumbGroupProps.Item[];

    setBreadCrumb: (breadCrumb: BreadcrumbGroupProps.Item[]) => void;
}

export const UserContext = createContext<UserContextType>({ user: null, setUser: () => { }, breadCrumb: [], setBreadCrumb: () => { } });



// User Context Provider component to wrap the application and make the user context available to all child components
export const UserContextProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<any>(null);
    const [busy, setBusy] = useState(true);
    const [breadCrumb, setBreadCrumb] = useState<BreadcrumbGroupProps.Item[]>([]);


    Hub.listen("auth", (data) => {
        if (data.payload.event === "signOut") {
            setUser(null);
        }
    });

    useEffect(() => {
        Hub.listen("auth", ({ payload: { event, data } }) => {
            if (event === "cognitoHostedUI") {
                checkUser();
            } else if (event === "signOut") {
                setUser(null);
            }
        });
        checkUser();
    }, []);

    const checkUser = async () => {
        try {
            const responseUser = await Auth.currentAuthenticatedUser();
            setUser(responseUser);
            setBusy(false);
        } catch (error) {
            setUser(null);
            setBusy(false);
        }
    };

    if (busy) {
        return <div>Loading...</div>
    } else {
        return (
            <UserContext.Provider value={{ user, setUser, breadCrumb, setBreadCrumb }}>
                {children}
            </UserContext.Provider>
        );
    }
}