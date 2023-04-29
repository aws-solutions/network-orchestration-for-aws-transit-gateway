# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [3.2.2] - 2023-04-14

### Added

#### Test Functionality
- Added test function - [`test_default_route_crud_operations.py - test_vpc_default_route_crud_operations_multiple_cidr_custom_destinations()`](./source/lambda/state_machine/__tests__/vpc_handler/test_default_route_crud_operations.py)
    - Tests the case where there are multiple custom CIDR blocks with a leading space between commas
- Added test function - [`test_default_route_crud_operations.py - test_vpc_default_route_crud_operations_multiple_pls_custom_destinations()`](./source/lambda/state_machine/__tests__/vpc_handler/test_default_route_crud_operations.py)
    - Tests the case where there are multiple prefix list IDs with a leading space between commas

### Changed

#### Core Functionality 
- Changed function - [`vpc_handler.py - _update_route_table_with_cidr_blocks()`](./source/lambda/state_machine/lib/handlers/vpc_handler.py)
    - Added `lstrip()` to routes to move leading white spaces enforced by the [`network-orchestration-hub.template's`](./deployment/network-orchestration-hub.template) `AllowedPattern` on the `ListOfCustomCidrBlocks` parameter
    - Added `and '' not in prefix_lists` and `and '' not in cidr_blocks` checks to account for empty environment variables (moto doesn't seem to catch this)

#### Test Functionality
- Changed test function - [`conftest.py - override_environment_variables()`](./source/lambda/state_machine/__tests__/conftest.py) 
    - Default Environment Variables changes for `os.environ['PREFIX_LISTS']`:
        - Syntax changed to match prefix syntax
        - Changed to only one entry - multiple entries are now environment overrides in the tests
- Changed test function - [`test_default_route_crud_operations.py - test_vpc_default_route_crud_operations_custom_destinations()`](./source/lambda/state_machine/__tests__/vpc_handler/test_default_route_crud_operations.py)
    - Added `Action` and `RouteTableId` to the test event.

# [3.2.2] - 2023-04-14

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
