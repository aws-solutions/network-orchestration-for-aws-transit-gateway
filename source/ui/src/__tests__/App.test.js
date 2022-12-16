/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/
import { Auth } from "@aws-amplify/auth";
import { render, screen, waitFor } from "@testing-library/react";
import { UserContext } from "../contexts/UserContext";
import App from "../App";
import userEvent from "@testing-library/user-event";
import { server } from "../setupTests";
import { graphql } from "msw";

jest.mock("@aws-amplify/auth");

let signInMockFunction;
let signOutMockFunction;

beforeEach(() => {
  signInMockFunction = jest.fn();
  signInMockFunction.mockReturnValue(new Promise(() => true));
  Auth.federatedSignIn = signInMockFunction;

  signOutMockFunction = jest.fn();
  signOutMockFunction.mockReturnValue(new Promise(() => true));
  Auth.signOut = signOutMockFunction;
});

function mockServerToReturnItems(items) {
  // Mock empty response for api call from landing page
  server.use(
    graphql.query("getDashboardItemsFromTransitNetworkOrchestratorTables", (req, res, ctx) => {
      return res(
        ctx.data({ getDashboardItemsFromTransitNetworkOrchestratorTables: { items: items, nextToken: null } })
      );
    })
  );
}

describe("when no user is logged in", () => {

  it("should redirect to login via Amplify Auth.federatedSignIn", () => {
    // ARRANGE
    mockServerToReturnItems([]);
    const userContextFalsy = {};

    // ACT
    render(
      <UserContext.Provider value={userContextFalsy}>
        <App />
      </UserContext.Provider>
    );

    // ASSERT
    const redirectMessage = screen.getByText(/Redirecting to login/i);
    expect(redirectMessage).toBeInTheDocument();

    expect(signInMockFunction).toHaveBeenCalledTimes(1);
  });
});

function mockUserContextWithGroups(newVar) {
  return { user: { signInUserSession: { idToken: { payload: { "cognito:groups": newVar } } } } };
}

describe("when a user is logged in", () => {

  beforeEach(() => {
    const userContextTruthy = mockUserContextWithGroups([]);

    mockServerToReturnItems([]);
    render(
      <UserContext.Provider value={userContextTruthy}>
        <App />
      </UserContext.Provider>
    );
  });

  it("should render header and navigation", async () => {

    // ASSERT
    expect(screen.queryAllByRole("navigation")).toHaveLength(2);
    expect(
      screen.queryByText(/Network Orchestration for AWS Transit Network/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Sign out/i })
    ).toBeInTheDocument();
  });

  describe("the Sign Out button", () => {

    it("should log out the user", async () => {
      // ARRANGE
      const signOutButton = screen.getByRole("link", { name: /Sign out/i });

      // ACT
      await userEvent.click(signOutButton);

      // ASSERT
      await waitFor(() => {
        expect(signOutMockFunction).toHaveBeenCalled();
      });
    });
  });
});
