// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React from 'react';
import {act, render, screen, waitFor} from "@testing-library/react"
import App from '../App';
import {UserContext, UserContextProvider} from '../components/context';
import userEvent from '@testing-library/user-event';
import {server} from "../setupTests";
import {graphql} from "msw";


const signInMockFunction = vi.fn().mockResolvedValue(undefined);
const signOutMockFunction = vi.fn().mockResolvedValue(undefined);

vi.mock("aws-amplify/auth", () => ({
    signInWithRedirect: (...args: any[]) => signInMockFunction(...args),
    signOut: (...args: any[]) => signOutMockFunction(...args),
}));

describe('renders App Component', () => {
    let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

    beforeAll(() => {
        consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterAll(() => {
        consoleErrorSpy.mockRestore();
        consoleWarnSpy.mockRestore();
    });


    let userContext = {
        setUser: () => {
        },
        breadCrumb: [],
        setBreadCrumb: () => {
        }
    }

    beforeEach(() => {
        signInMockFunction.mockClear();
        signOutMockFunction.mockClear();
    })

    describe('when no user is logged in', () => {
        test('should redirect to login via signInWithRedirect', async () => {
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
            groups: newVar,
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