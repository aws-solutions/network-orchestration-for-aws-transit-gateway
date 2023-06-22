import {act, render, screen, within} from "@testing-library/react";
import React from "react";
import {server} from "../setupTests";
import {graphql} from "msw";
import VersionHistory from "../pages/version-history";
import data from "./TestData";

const dashboardItem1 = data.dashboardItem1;
const dashboardItem2 = data.dashboardItem2;

jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'), // use actual for all non-hook parts
    useParams: () => ({
        subnetId: "1234",
        vpcId: "1234"
    }),
}));


function mockServerToReturnItems(items: any) {
    server.use(
        graphql.query("GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
            return res.once(
                ctx.data({getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables: {items: items, nextToken: null}})
            );
        })
    );
}


describe("Version History", () => {
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



    it("On Version History Render", async () => {
        // ARRANGE
        mockServerToReturnItems([
            dashboardItem1,
            dashboardItem2
        ]);

        await act(async () => {
            render(<VersionHistory/>);
        });

        expect(screen.getByRole('heading', {name: /Version History/i})).toBeInTheDocument();
    });

});