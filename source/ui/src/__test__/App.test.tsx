// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import {act, render, screen, waitFor} from "@testing-library/react"
import App from '../App';
import {UserContext, UserContextProvider} from '../components/context';
import {Auth} from 'aws-amplify';
import userEvent from '@testing-library/user-event';
import {server} from "../setupTests";
import {graphql} from "msw";


jest.mock("@aws-amplify/auth");

describe('renders App Component', () => {
    let consoleErrorSpy: jest.SpyInstance<void, [message?: any, ...optionalParams: any[]], any>;
    let consoleWarnSpy: jest.SpyInstance<void, [message?: any, ...optionalParams: any[]], any>;

    beforeAll(() => {
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
        consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterAll(() => {
        consoleErrorSpy.mockRestore();
        consoleWarnSpy.mockRestore();
    });

    let signInMockFunction: jest.Mock;
    let signOutMockFunction: jest.Mock;


    let userContext = {
        setUser: () => {
        },
        breadCrumb: [],
        setBreadCrumb: () => {
        }
    }

    beforeEach(() => {
        signInMockFunction = jest.fn();
        signInMockFunction.mockReturnValue(new Promise(() => true));
        Auth.federatedSignIn = signInMockFunction;

        signOutMockFunction = jest.fn();
        signOutMockFunction.mockReturnValue(new Promise(() => true));
        Auth.signOut = signOutMockFunction;
    })

    describe('when no user is logged in', () => {
        test('should redirect to login via Amplify Auth.federatedSignIn', async () => {
            // ARRANGE
            const userContextFalsy = null;

            // ACT
            await act(async () => render(
                <UserContext.Provider value={{
                    user: userContextFalsy,
                    ...userContext
                }}>
                    <App/>
                </UserContext.Provider>
            ));

            // ASSERT
            const redirectMessage = screen.getByText(/Redirecting to login/i);
            expect(redirectMessage).toBeInTheDocument();
            expect(signInMockFunction).toHaveBeenCalledTimes(1);
        });
    })


    const username = "adminuser"
    function mockUserContextWithGroups(newVar: any) {
        return {
            username: username,
            user: {signInUserSession: {idToken: {payload: {"cognito:groups": newVar}}}}
        };
    }

    function mockServerResponse(item: any) {
        server.use(
            graphql.query("getDashboardItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
                return res(
                    ctx.data({getDashboardItemsFromTransitNetworkOrchestratorTables: {items: item, nextToken: null}})
                );
            })
        )
    }

    describe("User Context Test", () => {
        it("should render the App component with the user context", async () => {
            render(
                <UserContextProvider>
                    <App/>
                </UserContextProvider>
            )
        });
    })

    describe('when user is logged in', () => {
        beforeEach(() => {
            const userContextTruthy = mockUserContextWithGroups([]);
            mockServerResponse([]);

            // ACT
            render(
                <UserContext.Provider value={{
                    user: userContextTruthy,
                    ...userContext
                }}>
                    <App/>
                </UserContext.Provider>
            );
        })


        describe('Side Navigation', () => {

        });

        describe('Sign Out button', () => {

            it('should be displayed after click on the username', async () => {
                await act(async () => {
                    await userEvent.click(screen.getByRole('button', {name: username}));
                });


                // ASSERT
                const signOutButton = await screen.findByRole('menuitem', {name: /Sign out/i});
                expect(signOutButton).toBeInTheDocument();

                expect(signOutMockFunction).not.toHaveBeenCalled();
            });


            it('should log out the user', async () => {
                await act(async () => {
                    await userEvent.click(screen.getByRole('button', {name: username}));
                });

                await waitFor(async () => {
                    const signOutButton = screen.getByTestId("signout");
                    await userEvent.click(signOutButton);
                });
            });
        });


        describe("Route to Dashboard", () => {
            it('should display navigation links', () => {
                expect(screen.getByRole('link', {name: /Dashboard/i})).toBeInTheDocument();
                expect(screen.getByRole('link', {name: /Action Items/i})).toBeInTheDocument();
            });


            it('should display the dashboard page', async () => {
                await act(async () => {
                    await userEvent.click(screen.getByRole('link', {name: /Dashboard/i}));
                });

                expect(screen.getByRole('heading', {name: /Dashboard/i})).toBeInTheDocument();
            });


            it('should display the action items page', async () => {
                await act(async () => {
                    await userEvent.click(screen.getByRole('link', {name: /Action Items/i}));
                });

                expect(screen.getByRole('heading', {name: /Action Items/i})).toBeInTheDocument();
            });
        })
    })

})