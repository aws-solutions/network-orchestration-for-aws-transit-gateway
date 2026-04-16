// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {createContext, useEffect, useMemo, useState} from "react";
import {Amplify} from "aws-amplify";
import {getCurrentUser, fetchAuthSession, AuthUser} from "aws-amplify/auth";
import {Hub} from "aws-amplify/utils";
import {BreadcrumbGroupProps} from "@cloudscape-design/components";

// stno_config object is assembled by custom_resource_helper into stno_config.js and loaded by index.html
// contains aws_appsync and cognito auth configuration
// @ts-ignore
const config = window.stno_config;

if (config) {
    Amplify.configure({
        Auth: {
            Cognito: {
                userPoolId: config.aws_user_pools_id,
                userPoolClientId: config.aws_user_pools_web_client_id,
                identityPoolId: config.aws_cognito_identity_pool_id,
                loginWith: {
                    oauth: {
                        domain: config.Auth.oauth.domain,
                        scopes: config.Auth.oauth.scope,
                        redirectSignIn: [config.Auth.oauth.redirectSignIn],
                        redirectSignOut: [config.Auth.oauth.redirectSignOut],
                        responseType: config.Auth.oauth.responseType,
                    }
                }
            }
        },
        API: {
            GraphQL: {
                endpoint: config.aws_appsync_graphqlEndpoint,
                region: config.aws_appsync_region,
                defaultAuthMode: "userPool",
            }
        }
    });
}

export type UserInfo = {
    username: string;
    groups: string[];
};

type UserContextType = {
    user: UserInfo | null;
    setUser: (user: UserInfo | null) => void;
    breadCrumb: BreadcrumbGroupProps.Item[];
    setBreadCrumb: (breadCrumb: BreadcrumbGroupProps.Item[]) => void;
}

export const UserContext = createContext<UserContextType>({ user: null, setUser: () => { }, breadCrumb: [], setBreadCrumb: () => { } });

// User Context Provider component to wrap the application and make the user context available to all child components
export const UserContextProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<UserInfo | null>(null);
    const [busy, setBusy] = useState(true);
    const [breadCrumb, setBreadCrumb] = useState<BreadcrumbGroupProps.Item[]>([]);

    useEffect(() => {
        const unsubscribe = Hub.listen("auth", ({ payload }) => {
            if (payload.event === "signedIn") {
                checkUser();
            } else if (payload.event === "signedOut") {
                setUser(null);
            }
        });
        checkUser();
        return unsubscribe;
    }, []);

    const checkUser = async () => {
        try {
            const authUser: AuthUser = await getCurrentUser();
            const session = await fetchAuthSession();
            const groups = (session.tokens?.idToken?.payload["cognito:groups"] as string[]) || [];
            setUser({ username: authUser.username, groups });
            setBusy(false);
        } catch {
            setUser(null);
            setBusy(false);
        }
    };

    const contextValue = useMemo(() => ({ user, setUser, breadCrumb, setBreadCrumb }), [user, setUser, breadCrumb, setBreadCrumb]);

    if (busy) {
        return <div>Loading...</div>
    } else {
        return (
            <UserContext.Provider value={contextValue}>
                {children}
            </UserContext.Provider>
        );
    }
}
