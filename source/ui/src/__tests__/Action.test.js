/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/
import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import Action from "../Components/Action/Action";
import { server } from "../setupTests";
import { graphql } from "msw";
import { actionItem1, actionItem2 } from "./TestData";
import userEvent from "@testing-library/user-event";

function mockServerToReturnItems(items) {
  server.use(
    graphql.query("GetActionItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
      return res(
        ctx.data({ getActionItemsFromTransitNetworkOrchestratorTables: { items: items, nextToken: null } })
      );
    }),
    graphql.query("GetVersionHistoryForSubnetFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
      return res(
        ctx.data({ getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables: { items: [], nextToken: null } })
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

it("should render the Action view with a table", () => {
  // ARRANGE
  mockServerToReturnItems([]);

  // ACT
  render(
    <Action location={{ state: "foo,bar" }} />
  );

  // ASSERT
  expect(screen.getByRole("button", { name: (/Action/i) })).toBeInTheDocument();
  expect(screen.getByRole("grid")).toBeInTheDocument();
});


it("should render the items returned from API", async () => {
  // ARRANGE
  mockServerToReturnItems([
    actionItem1,
    actionItem2
  ]);

  // ACT
  render(
    <Action location={{ state: "foo,bar" }} />
  );
  await screen.findByRole("button", { name: (/refresh/i) });

  // ASSERT
  expect(await screen.findByText(/actionItem1/i)).toBeInTheDocument();
  expect(await screen.findByText(/actionItem2/i)).toBeInTheDocument();
});

it("should refresh on button click", async () => {
  // ARRANGE
  mockServerToReturnItems([]);
  render(
    <Action location={{ state: "foo,bar" }} />
  );

  const refreshButton = await screen.findByRole("button", { name: (/refresh/i) });
  mockServerToReturnItems([
    actionItem1,
    actionItem2
  ]);

  // ACT
  await userEvent.click(refreshButton);

  // ASSERT
  await expectRefreshButtonToDisappearAndReappear();
  expect(await screen.findByText(/actionItem1/i)).toBeInTheDocument();
  expect(await screen.findByText(/actionItem2/i)).toBeInTheDocument();
});

async function expectRefreshButtonToDisappearAndReappear() {
  expect(screen.queryByRole("button", { name: (/refresh/i) })).not.toBeInTheDocument();
  expect(await screen.findByRole("button", { name: (/refresh/i) })).toBeInTheDocument();
}

describe("version history", () => {

  it("should open the history modal", async () => {
    // ARRANGE
    mockServerToReturnItems([
      actionItem1,
      actionItem2
    ]);

    render(
      <Action location={{ state: "foo,bar" }} />
    );

    const row1 = await screen.findByText(/actionItem1/i);
    const actionButton = await screen.findByRole("button", { name: (/Action/i) });
    await userEvent.click(actionButton);
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

  it("should open the history modal as Admin", async () => {
    // ARRANGE
    mockServerToReturnItems([
      actionItem1,
      actionItem2
    ]);

    render(
      <Action location={{ state: "foo,AdminGroup" }} />
    );

    const row1 = await screen.findByText(/actionItem1/i);
    await userEvent.click(row1);
    await userEvent.click(row1);

    const actionButton = await screen.findByRole("button", { name: (/Action/i) });
    await userEvent.click(actionButton);

    const historyButton = await screen.findByRole("button", { name: (/View History/i) });

    // ACT
    await userEvent.click(row1);
    await userEvent.click(historyButton);

    // ASSERT
    expect(await screen.findByText(/Version History/i)).toBeInTheDocument();
  });

});

async function openMenuAndFindItem(openMenuButtonName, menuItemName) {
  const openMenuButton = await screen.findByRole("button", { name: openMenuButtonName });
  await userEvent.click(openMenuButton);

  return await screen.findByRole("button", { name: menuItemName });
}

describe("accepting a request", () => {

  it("should ask for confirmation", async () => {
    // ARRANGE
    mockServerToReturnItems([
      actionItem1,
      actionItem2
    ]);

    render(
      <Action location={{ state: "foo,AdminGroup" }} />
    );

    const row1 = await screen.findByText(/actionItem1/i);
    await userEvent.click(row1);

    const acceptButton = await openMenuAndFindItem(/Action/i, /Approve/i);

    // ACT
    await userEvent.click(acceptButton);

    // ASSERT
    expect(await screen.findByText(/Are you sure you want to accept this request?/i)).toBeInTheDocument();

    const modal = await screen.findByRole("dialog", { name: (/Confirmation/i) });
    const cancelButton = await within(modal).findByRole("button", { name: (/Cancel/i) });

    // ACT
    await userEvent.click(cancelButton);

    // ASSERT
    await userEvent.click(acceptButton);
    expect(await screen.findByText(/Are you sure you want to accept this request?/i)).toBeInTheDocument();

    const acceptModal = await screen.findByRole("dialog", { name: (/Confirmation/i) });
    const acceptConfirmButton = await within(acceptModal).findByRole("button", { name: (/Approve/i) });

    await userEvent.click(acceptConfirmButton);

    await waitFor(() => {
      expect(screen.queryByText(/Confirmation/i)).not.toBeInTheDocument();
    });
  });
});

describe("rejecting a request", () => {

  it("should ask for confirmation", async () => {
    // ARRANGE
    mockServerToReturnItems([
      actionItem1,
      actionItem2
    ]);

    render(
      <Action location={{ state: "foo,AdminGroup" }} />
    );

    const row1 = await screen.findByText(/actionItem1/i);
    await userEvent.click(row1);

    const rejectButton = await openMenuAndFindItem(/Action/i, /Reject/i);

    // ACT
    await userEvent.click(rejectButton);

    // ASSERT
    expect(await screen.findByText(/Are you sure you want to reject this request?/i)).toBeInTheDocument();

    const modal = await screen.findByRole("dialog", { name: (/Confirmation/i) });
    const cancelButton = await within(modal).findByRole("button", { name: (/Cancel/i) });

    // ACT
    await userEvent.click(cancelButton);

    // ASSERT
    await userEvent.click(rejectButton);
    expect(await screen.findByText(/Are you sure you want to reject this request?/i)).toBeInTheDocument();

    const rejectModal = await screen.findByRole("dialog", { name: (/Confirmation/i) });
    const rejectConfirmButton = await within(rejectModal).findByRole("button", { name: (/Reject/i) });

    await userEvent.click(rejectConfirmButton);

    await waitFor(() => {
      expect(screen.queryByText(/Confirmation/i)).not.toBeInTheDocument();
    });
  });

});
