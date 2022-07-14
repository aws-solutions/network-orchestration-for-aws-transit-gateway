// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {logger} from "./lib/logger";
import {AdminAddUserToGroupCommand, CognitoIdentityProviderClient} from "@aws-sdk/client-cognito-identity-provider";
import {UserAgent} from "@aws-sdk/types";

export interface IHandlerInput {
  userPoolId: string;
  userName: string;
  triggerSource: string;
  region: string;
  request: {
    userAttributes: {
      sub?: string;
      email_verified: string;
      "cognito:user_status": string;
      identities: string;
    };
  };
}


function isExternalUserLoggingInForTheFirstTime(event: IHandlerInput): boolean {
  return event.triggerSource === "PostConfirmation_ConfirmSignUp" &&
    event.request.userAttributes["cognito:user_status"] ===
    "EXTERNAL_PROVIDER";
}

export const READ_ONLY_USER_GROUP = 'ReadOnlyUserGroup'; // GroupName of UserPoolGroupReadOnlyUsers from cf template

async function addUserToReadOnlyUserGroup(event: IHandlerInput) {
  logger.debug("Handling federated user");
  const userAgent: UserAgent = [[`AWSSOLUTION/${process.env.SOLUTION_ID || ''}`,`${process.env.SOLUTION_VERSION}` || '']];
  const configuration = {region: event.region, customUserAgent: userAgent};
  const client = new CognitoIdentityProviderClient(configuration);
  const command = new AdminAddUserToGroupCommand({
    UserPoolId: event.userPoolId,
    Username: event.userName,
    GroupName: READ_ONLY_USER_GROUP
  });
  await client.send(command);
}

export async function handler(event: IHandlerInput): Promise<any> {
  logger.debug(
    `Received event: ${JSON.stringify(event, null, 2)}`
  );
  if (
    isExternalUserLoggingInForTheFirstTime(event)
  ) {
    await addUserToReadOnlyUserGroup(event);
  }
}
