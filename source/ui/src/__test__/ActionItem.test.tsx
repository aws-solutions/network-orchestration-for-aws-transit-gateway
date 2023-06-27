// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, {useContext} from 'react';
import {act, render, screen, waitFor} from "@testing-library/react"
import {server} from "../setupTests";
import {graphql} from "msw";
import ActionItems from "../pages/action-items";
import data from "./TestData";
import userEvent from "@testing-library/user-event";

jest.mock("@aws-amplify/auth");

const actionItem1 = data.actionItem1;
const actionItem2 = data.actionItem2;

const mockedUsedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useNavigate: () => mockedUsedNavigate,
}));


function mockUserContextWithGroups(newVar: any) {
    return {
        attributes: {email: "test"},
        signInUserSession: {idToken: {payload: {"cognito:groups": newVar}}}
    };
}


function getUserContext(group: any) {
    return {
        setUser: () => {
        },
        breadCrumb: [],
        setBreadCrumb: () => {
        },
        user: mockUserContextWithGroups(group)
    };
}

function mockServerToReturnItems(items: any) {
    server.use(
        graphql.query("GetActionItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
            return res(
                ctx.data({getActionItemsFromTransitNetworkOrchestratorTables: {items: items, nextToken: null}})
            );
        }),
        graphql.query("GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
            return res(
                ctx.data({getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables: {items: [], nextToken: null}})
            );
        }),
        graphql.mutation("UpdateTransitNetworkOrchestratorTable", (req, res, ctx) => {
            return res(
                ctx.data({
                    updateTransitNetworkOrchestratorTable: {
                        updateTransitNetworkOrchestratorTable: {},
                        nextToken: null
                    }
                })
            );
        })
    );
}


jest.mock('react', () => ({
    ...jest.requireActual('react'),
    useContext: jest.fn(),
}));


describe("Action Items", () => {

    let consoleErrorSpy: jest.SpyInstance<void, [message?: any, ...optionalParams: any[]], any>;
    let consoleWarnSpy: jest.SpyInstance<void, [message?: any, ...optionalParams: any[]], any>;

    beforeAll(() => {
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {
        });
        consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {
        });
    });

    afterAll(() => {
        consoleErrorSpy.mockRestore();
        consoleWarnSpy.mockRestore();
    });

    describe("Action Items without admin group", () => {
        beforeEach(() => {

            // @ts-ignore
            useContext.mockReturnValue(getUserContext([]));
            mockServerToReturnItems([
                actionItem1,
                actionItem2
            ]);

            render(
                <ActionItems/>
            )
        });

        it("should render the Action view with a table", async () => {
            await waitFor(async () => {
                expect(await screen.getByText(/Action Items/i)).toBeInTheDocument();
                expect(await screen.findByRole("button", {name: (/refresh/i)})).toBeInTheDocument();
            })
        });


        it("should render the items returned from API", async () => {
            await waitFor(async () => {
                await screen.findByRole("button", {name: (/refresh/i)});

                expect(await screen.findByText(/actionItem1/i)).toBeInTheDocument();
                expect(await screen.findByText(/actionItem2/i)).toBeInTheDocument();
            })
        });

        it("does not show the action button in the screen", async () => {
            await waitFor(async () => {
                expect(await screen.queryByRole("button", {name: (/action/i)})).not.toBeInTheDocument();
            })
        });


        it("should refresh on button click", async () => {
            mockServerToReturnItems([
                actionItem1,
                actionItem2
            ]);
            const refreshButton = await screen.findByRole("button", {name: (/refresh/i)});
            await act(async () => {
                mockServerToReturnItems([
                    actionItem1,
                    actionItem2
                ]);
                await userEvent.click(refreshButton);
            });
        });

    });
    describe("Action Items with admin group", () => {
        beforeEach(() => {

            // @ts-ignore
            useContext.mockReturnValue(getUserContext(["AdminGroup"]));
            mockServerToReturnItems([
                actionItem1,
                actionItem2
            ]);

            render(
                <ActionItems/>
            )
        });

        it("should render the action button", async () => {

            const table = await screen.findAllByRole("radio");
            await act(() => {
                userEvent.click(table[0]);
            });
            await waitFor(async () => {
                expect(await screen.getByText(/Action Items/i)).toBeInTheDocument();
            })
        });
    });

});