# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2022-06-17

### Added
- CF template allows to connect external SAML identity provider to cognito user pool
- If SAML IdP is used, cognito-trigger function will add any federated user to ReadOnlyUserGroup after first login
- Added WAF protection to the CloudFront distribution
- Added Security relevant http headers in CloudFront responses

### Changed
- Creation of ServiceLinkedRole can be skipped if it exists in spoke account
- Web UI will utilize Cognito Hosted UI instead of Amplify Authenticator component

## [3.0.1] - 2022-04-15

### Changed

- dependency versions and package-lock.json to address dependabot identified CVEs

## [3.0.0] - 2022-03-25

### Added

- Tagging the Transit Gateway attachment with "Name" on both the hub and spoke accounts; with the account name, the AWS Organizations OU path and the VPC name
- _ListOfVpcTagsForAttachment_ CloudFormation parameter to specify a comma separated list of tags which if found in the VPC, will be copied across to the TGW attachments
- Support for Organizations Tag policies
- STNO state machine [logging using CloudWatch logs](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)

### Changed

- Improved reliability. Fixed race conditions (issue [#1](https://github.com/aws-solutions/serverless-transit-network-orchestrator/issues/1)).
- Conditional auto-approval or auto-reject rules based on AWS Organizations OU membership, with separate rules for associations and propagations.
- Events now logged in CloudWatch Logs in addition to DynamoDB; to enable searching with CloudWatch Log Insights
- Allow VPCs deployed using CloudFormation, that has the STNO tags, to be deleted. This is done by triggering a deletion of the transit gateway attachment when CloudFormation attempts to delete the subnet.
- Transit Gateway peering feature now implemented using AWS Lambda
- Pinned dependency versions for deterministic builds

### Removed

- CloudFormation parameters for log retention days have been moved to _mappings_ section of the template
- SSM Parameter Store for _UUID_ and _SendMetrics_ flag. Both now added as environment variable to lambda functions

## [2.0.0] - 2020-08-20

- Ability to peer inter-region transit gateways by tagging the transit gateway.
- Option to use an existing transit gateway.
- Ability to create or use existing global network.
- Register the transit gateway with the global network.
- Ability to add custom CIDR blocks to the VPC route tables in the spoke accounts.
- Ability to add customer-managed prefix lists to the VPC route tables in spoke accounts.

## [1.0.0] - 2019-09-10

- Initial public release
