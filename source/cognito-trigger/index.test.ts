// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {handler, IHandlerInput, READ_ONLY_USER_GROUP} from "./index";
import {mockClient} from "aws-sdk-client-mock";
import {AdminAddUserToGroupCommand, CognitoIdentityProviderClient} from "@aws-sdk/client-cognito-identity-provider";

describe("cognito-trigger", function () {

  let cognitoClientMock;
  beforeEach(() => {
    cognitoClientMock = mockClient(CognitoIdentityProviderClient);
    cognitoClientMock.on(AdminAddUserToGroupCommand).resolves();
  });

  it("should add federated users to ReadOnlyUserGroup", async function () {
    // given
    const event: IHandlerInput = {
      userPoolId: "user-pool-id",
      userName: "user-name",
      triggerSource: "PostConfirmation_ConfirmSignUp",
      region: "us-east-1",
      request: {
        userAttributes: {
          "cognito:user_status": "EXTERNAL_PROVIDER",
          email_verified: "false",
          identities: "",
          sub: "user-uuid",
        },
      },
    };

    // when
    await handler(event);

    // then
    expect(cognitoClientMock.calls()).toHaveLength(1);
    let command = cognitoClientMock.call(0).firstArg;
    expect(command).toBeInstanceOf(
      AdminAddUserToGroupCommand
    );
    expect(command.input).toEqual({
      "UserPoolId": event.userPoolId,
      "Username": event.userName,
      "GroupName": READ_ONLY_USER_GROUP
    });
  });

  it("should not call Cognito for non federated users", async function () {

    // given
    const event: IHandlerInput = {
      userPoolId: "user-pool-id",
      userName: "user-name",
      triggerSource: "trigger-src",
      region: "us-east-1",
      request: {
        userAttributes: {
          "cognito:user_status": "CONFIRMED",
          email_verified: "false",
          identities: "",
          sub: "user-uuid",
        },
      },
    };

    // when
    await handler(event);

    // then
    expect(cognitoClientMock.calls()).toHaveLength(0);
  });
});
