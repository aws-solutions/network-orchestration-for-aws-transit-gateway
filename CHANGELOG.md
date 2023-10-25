# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.3] - 2023-10

### Changed
- Updated Lambda Function runtime to Python 3.11 and Node.js 18
- Tags for Application in AppRegistry

### Fixed
- Upgrade @babel/traverse to mitigate CVE-2023-45133
- Upgrade urllib3 to mitigate CVE-2023-45803

## [3.3.2] - 2023-10

### Added
New CloudFormation parameter to allow users to skip transit gateway registration with the global network. 

### Fixed
Updated package versions to resolve security vulnerabilities. 

## [3.3.1] - 2023-07-21

### Changed
- Move the service linked roles from hub and spoke stacks to separate stacks to allow 
  multi-region deployments and avoid 'AlreadyExists' error. 

## [3.3] - 2023-06-28

### Added
- Support for new routing tag (route-to-tgw) that allows users to update route table for secondary subnets in the 
  same availability zone.
- Support to update main route table associated with the subnets in the VPC.
- Support for new regions - Beijing, Ningxia and Stockholm.
- Option to deploy the solution without Web UI.
- Option to disable Transit Gateway resource sharing with external principals.
- Allow disabling Transit Gateway resource sharing with external principals.
- Ability to enable MFA for Cognito User Pool

### Changed
- Updated Web UI console using CloudScape design system.
- Step Function execution name to reflect create or delete tagging action.
- Enabled X-Ray for Step Functions and AppSync GraphQL API
- Improve error handling in Step Functions to create Transit Gateway route table associations.
- Refactor VPC-TGW Attachment modules for maintainability.
- Refactor exception handling - use decorator in the BOTO3 client modules.
- AppRegistry Attribute Group name with a unique string.

### Fixed
- Allow spaces in CloudFormation parameters - CIDR blocks and Prefix Lists.
- Ability to register new and existing transit gateways with existing global network.
- GitHub Issues: #38, #39, #49, #50, #56, #60, #73, #77, #78, #81

## [3.2.2] - 2023-04-14

### Added

- ObjectWriter ownership control to logs bucket, in response to S3 service change

## [3.2.1] - 2023-01-13

### Changed

- Updated python requests to 2.28.1 due to security patch required for certifi module which is a dependency. Using the latest requests version 2.28.1 installs the latest patched version of certifi v2022.12.07. For details please refer to https://nvd.nist.gov/vuln/detail/cve-2022-23491.
- package-lock.json to address dependabot identified vulnerabilities

## [3.2.0] - 2022-11-25

### Added

- Support for App Registry
- Unit tests for ui and lambda

### Changed

- Solution name from Serverless Transit Network Orchestrator (STNO) to **Network Orchestration for AWS Transit Gateway**
- package-lock.json to address dependabot identified vulnerabilities
- testing-requirements.txt to address dependabot identified vulnerabilities

## [3.1.1] - 2022-10-18

### Changed

- package-lock.json to address dependabot identified vulnerabilities

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
