/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/
import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import Dashboard from "../Components/Dashboard/Dashboard";
import "@testing-library/jest-dom";
import { graphql } from "msw";
import { server } from "../setupTests";
import userEvent from "@testing-library/user-event";
import { dashboardItem1, dashboardItem2 } from "./TestData";

function mockServerToReturnItems(items) {
  server.use(
    graphql.query("getDashboardItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
      return res.once(
        ctx.data({ getDashboardItemsFromTransitNetworkOrchestratorTables: { items: items, nextToken: null } })
      );
    }),
    graphql.query("GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
      return res.once(
        ctx.data({ getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables: { items: [], nextToken: null } })
      );
    })
  );
}


it("should render the Dashboard with a table", async () => {
  // ARRANGE
  mockServerToReturnItems([]);

  // ACT
  render(<Dashboard />);

  // ASSERT
  expect(screen.queryByRole("button", { name: (/View History/i) })).toBeInTheDocument();
  expect(screen.queryByRole("grid")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: (/refresh/i) })).toBeInTheDocument();
});

it("should render the items returned from API", async () => {
  // ARRANGE
  mockServerToReturnItems([
    dashboardItem1,
    dashboardItem2
  ]);

  // ACT
  render(<Dashboard />);
  await screen.findByRole("button", { name: (/refresh/i) });

  // ASSERT
  expect(await screen.findByText(/dashboardItem1/i)).toBeInTheDocument();
  expect(await screen.findByText(/dashboardItem2/i)).toBeInTheDocument();
});

async function expectRefreshButtonToDisappearAndReappear() {
  expect(screen.queryByRole("button", { name: (/refresh/i) })).not.toBeInTheDocument();
  expect(await screen.findByRole("button", { name: (/refresh/i) })).toBeInTheDocument();
}

it("should refresh on button click", async () => {
  // ARRANGE
  mockServerToReturnItems([]);

  render(<Dashboard />);
  const refreshButton = await screen.findByRole("button", { name: (/refresh/i) });

  mockServerToReturnItems([
    dashboardItem1,
    dashboardItem2
  ]);

  // ACT
  await userEvent.click(refreshButton);

  // ASSERT
  await expectRefreshButtonToDisappearAndReappear();
  expect(await screen.findByText(/dashboardItem1/i)).toBeInTheDocument();
  expect(await screen.findByText(/dashboardItem2/i)).toBeInTheDocument();
});

it("should open the history modal", async () => {
  // ARRANGE
  mockServerToReturnItems([dashboardItem1, dashboardItem2]);

  render(<Dashboard />);

  const row1 = await screen.findByText(/dashboardItem1/i);
  const historyButton = await screen.findByRole("button", { name: (/View History/i) });

  // ACT
  await userEvent.click(row1);
  await userEvent.click(historyButton);

  // ASSERT
  const modal = await screen.findByRole("dialog", { name: (/Version History/i) });
  expect(await modal).toBeInTheDocument();

  const closeButton = (await within(modal).findAllByRole("button", { name: (/Close/i) }))[0];
  await userEvent.click(closeButton);
  await waitFor(() => {
    expect(screen.queryByText(/Version History/i)).not.toBeInTheDocument();
  });
});