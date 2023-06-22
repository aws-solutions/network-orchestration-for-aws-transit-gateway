// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import "@testing-library/jest-dom";

import Amplify from "@aws-amplify/core";
import { setupServer } from "msw/node";

export const server = setupServer();

// Establish API mocking before all tests.
beforeAll(() => {
    server.listen();
    Amplify.configure({
        "aws_user_pools_id": "us-east-1_xEEQi6J0U",
        "aws_user_pools_web_client_id": "1p4fndmnt1if15dsfbbd232rfs",
        "aws_cognito_identity_pool_id": "us-east-1:0e7a3f0d-45f5-4ff6-b5b1-d3eceda8743d",

        "aws_appsync_graphqlEndpoint": "http://localhost",
        "aws_appsync_authenticationType": "NONE"
    });
});

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished.
afterAll(() => server.close());