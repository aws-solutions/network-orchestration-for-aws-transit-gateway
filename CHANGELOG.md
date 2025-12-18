# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.21] - 2025-12-18

### Changed

- Enhanced operational metrics sent by the solution to include Transit Gateway attachment metrics

### Security

- Bump `node-forge` to address [CVE-2025-12816] (<https://avd.aquasec.com/nvd/2025/cve-2025-12816>) and [CVE-2025-66031] (<https://avd.aquasec.com/nvd/2025/cve-2025-66031>)
- Bump `werkzeug` to address [CVE-2025-66221] (<https://avd.aquasec.com/nvd/2025/cve-2025-66221>)
- Bump `urllib3` to address [CVE-2025-66418] (<https://avd.aquasec.com/nvd/2025/cve-2025-66418>) and [CVE-2025-66471] (<https://avd.aquasec.com/nvd/2025/cve-2025-66471>)

## [3.3.20] - 2025-11-25

### Security

- Bumped glob to `^11.1.0` to mitigate [CVE-2025-64756](https://avd.aquasec.com/nvd/cve-2025-64756)
- Bumped js-yaml to `^4.1.1` to mitigate [CVE-2025-64718](https://avd.aquasec.com/nvd/cve-2025-64718)

## [3.3.19] - 2025-09-18

### Security

- Bumped axios to `1.12.1` to mitigate [CVE-2025-58754](https://avd.aquasec.com/nvd/cve-2025-58754)

### Changed

- package-lock.json to address dependabot identified vulnerabilities

## [3.3.18] - 2025-07-30

### Security

- Bump `form-data` to address [CVE-2025-7783] (<https://avd.aquasec.com/nvd/cve-2025-7783>)
- Bump `brace-expansion` to address [CVE-2025-5889]
- Bump `urllib3` to address [CVE-2025-50181], [CVE-2025-50182] (<https://avd.aquasec.com/nvd/cve-2025-50181>), (<https://avd.aquasec.com/nvd/cve-2025-50182>)

### Removed

- AppRegistry application tags at resource level

## [3.3.17] - 2025-06-10

### Security

- Bump `webpack-dev-server` to mitigate [CVE-2025-30360](https://avd.aquasec.com/nvd/cve-2025-30360)

### Changed

- Remove `requirements.txt` in favor of `poetry.lock` for dependency management with poetry
- Refactor `lambda` as standard python package with poetry

## [3.3.16] - 2025-05-30

### Security

- Bump http-proxy-middleware to `2.0.9` to mitigate [CVE-2025-32997](https://github.com/advisories/GHSA-9gqv-wp59-fq42)

### Fixed

- Remove setuptools and pkg_resources from lambda packaging
- Remove event verbose log at `INFO` level
- Respect tag case when copying vpc tags on TGW attachments
- Add dependency for CSP resource on `DeployWebUiCondition`

## [3.3.15] - 2025-04-05

### Security

- Bump aws-amplify to `5.3.27`
- Allow only TLS requests on S3 bucket through bucket policy
- Add CSP security headers on CloudFront
- Enable MFA for authentication by default
- Add [AWS Managed WAF rules](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-list.html) to ACL
- Disable introspection queries on AppSync endpoint

### Changed

- Disable verbose logging on the AppSync endpoint
- AppRegistry application tags at resource level

### Fixed

- Remove unused http methods from cache behavior, Cloudfront only needs to process and forward GET/HEAD requests to S3 origin
- Improve error response for `UpdateTransitNetworkOrchestratorTable` API path

## [3.3.14] - 2025-03-14

### Security

- Bumped axios to `1.8.2` to mitigate [CVE-2025-27152](https://github.com/axios/axios/security/advisories/GHSA-jr5f-v2jv-69x6)
- Bumped @babel/runtime, @babel/helpers to `7.26.10` to mitigate [CVE-2025-27789](https://github.com/babel/babel/security/advisories/GHSA-968p-4wvh-cqc8)

## [3.3.13] - 2025-02-06

### Security

- Bumped path-to-regexp to `0.1.12` to mitigate [CVE-2024-52798](https://github.com/advisories/GHSA-rhx6-c78j-4q9w)
- Bumped nanoid to `3.3.8` to mitigate [CVE-2024-55565](https://github.com/advisories/GHSA-mwcw-c2x4-8c55)

## [3.3.12] - 2024-11-22

### Security

- Bumped cross-spawn to `7.0.6` to mitigate [CVE-2024-21538](https://avd.aquasec.com/nvd/cve-2024-21538)

## [3.3.11] - 2024-10-31

### Security

- Bumped http-proxy-middleware to `2.0.7` to mitigate [CVE-2024-21536](https://github.com/advisories/GHSA-c7qv-q95q-8v27)

### Changed

- Moved spoke service linked role template as conditional nested stack under spoke stack

## [3.3.10] - 2024-10-10

### Security

- Bumped rollup to `2.79.2` to mitigate [CVE-2024-47068](https://github.com/advisories/GHSA-gcx4-mw62-g8wm)

## [3.3.9] - 2024-09-16

### Security

- Bumped micromatch to `4.0.8` to mitigate [CVE-2024-4067](https://github.com/advisories/GHSA-952p-6rrq-rcjv)
- Bumped webpack to `5.94.0` to mitigate [CVE-2024-43788](https://github.com/advisories/GHSA-4vvj-4cpr-p986)
- Bumped express to `4.21.0` to mitigate CVEs in sub-dependencies
- Bump path-to-regexp to `6.3.0` to address [CVE-2024-45296](https://github.com/advisories/GHSA-9wv6-86v2-598j)

## [3.3.8] - 2024-08-15

### Fixed

- [#116](https://github.com/aws-solutions/network-orchestration-for-aws-transit-gateway/issues/116)
- [#117](https://github.com/aws-solutions/network-orchestration-for-aws-transit-gateway/issues/117)
- IAM policy for _StateMachineLambdaFunctionRole_

### Changed

- `resource_exception_handler` decorator does not catch `IncorrectState`
  exception, allowing the exception to be raised as `ResourceBusyException`
  by `service_exception_handler` decorator

### Security

- Bumped axios to `1.7.4` to mitigate [CVE-2024-39338](https://github.com/advisories/GHSA-8hc4-vh64-cxmj)

## [3.3.7] - 2024-08-02

### Security

- Bumped fast-xml-parser to `4.4.1` to mitigate [CVE-2024-41818](https://avd.aquasec.com/nvd/cve-2024-41818)

## [3.3.6] - 2024-06-25

### Changed

- Bumped jest to `29.7.0`
- Bumped ts-jest to `29.1.4`
- Bumped boto3 to `1.34.129`
- Bumped botocore to `1.34.129`

### Security

- Bumped ejs to `3.1.10` to mitigate [CVE-2024-33883](https://avd.aquasec.com/nvd/cve-2024-33883)
- Bumped `ws` to resolve [CVE-2024-37890]

## [3.3.5] - 2024-04-24

### Added

- Validation of transit gateway route table names to improve error message in case of duplicate names

### Changed

- Removed dependency on 'requests' library to mitigate CVE-2024-3651

## [3.3.4] - 2024-04-03

### Fixed

- Upgrade webpack-dev-middleware to mitigate CVE-2024-29180

## [3.3.3] - 2023-10-25

### Changed

- Updated Lambda Function runtime to Python 3.11 and Node.js 18
- Tags for Application in AppRegistry

### Fixed

- Upgrade @babel/traverse to mitigate CVE-2023-45133
- Upgrade urllib3 to mitigate CVE-2023-45803

## [3.3.2] - 2023-10-03

### Added

- New CloudFormation parameter to allow users to skip transit gateway
  registration with the global network.

### Fixed

- Updated package versions to resolve security vulnerabilities.

## [3.3.1] - 2023-07-21

### Changed

- Move the service linked roles from hub and spoke stacks to separate stacks to allow
  multi-region deployments and avoid 'AlreadyExists' error.

## [3.3.0] - 2023-06-28

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

- Updated python requests to 2.28.1 due to security patch required for
  certifi module which is a dependency. Using the latest requests version 2.
  28.1 installs the latest patched version of certifi v2022.12.07. For
  details please refer to [CVE-2022-23491](https://nvd.nist.gov/vuln/detail/cve-2022-23491).
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

- Improved reliability. Fixed race conditions (issue [#1](https://github.com/aws-solutions/network-orchestration-for-aws-transit-gateway/issues/1)).
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
