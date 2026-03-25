// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import {act, render, screen, waitFor, within} from "@testing-library/react";
import "@testing-library/jest-dom";
import {graphql} from "msw";
import {server} from "../setupTests";
import userEvent from "@testing-library/user-event";
import data from "./TestData";
import Dashboard from "../pages/dashboard";


const dashboardItem1 = data.dashboardItem1;
const dashboardItem2 = data.dashboardItem2;

const mockedUsedNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
    ...vi.importActual('react-router-dom'),
    useNavigate: () => mockedUsedNavigate,
}));

function mockServerToReturnItems(items: any) {
    server.use(
        graphql.query("getDashboardItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
            return res(
                ctx.data({getDashboardItemsFromTransitNetworkOrchestratorTables: {items: items, nextToken: null}})
            );
        }),
        graphql.query("GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
            return res(
                ctx.data({getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables: {items: [], nextToken: null}})
            );
        })
    );
}


describe("Dashboard", () => {
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



    it("should render the Dashboard with a table", async () => {
        // ARRANGE
        mockServerToReturnItems([]);

        await act(async () => {
            render(<Dashboard/>);
        });

        expect(await screen.findByRole("button", {name: (/refresh/i)})).toBeInTheDocument();
    });

    it("should render the items returned from API", async () => {
        // ARRANGE
        mockServerToReturnItems([
            dashboardItem1,
            dashboardItem2
        ]);

        await act(async () => {
            render(<Dashboard/>);
        });

        await screen.findByRole("button", {name: (/refresh/i)});

        // ASSERT
        expect(await screen.findByText(/dashboardItem1/i)).toBeInTheDocument();
        expect(await screen.findByText(/dashboardItem2/i)).toBeInTheDocument();
    });


    it("should refresh on button click", async () => {
        // ARRANGE
        mockServerToReturnItems([]);

        await act(async () => {
            render(<Dashboard/>);
        });

        const refreshButton = await screen.findByRole('button', {name: 'Refresh'});

        await act(async () => {
            await userEvent.click(refreshButton);
        });



        // ASSERT
        await waitFor(() => {
            expect(screen.queryByText(/dashboardItem1/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/dashboardItem2/i)).not.toBeInTheDocument();
        });

    });

});