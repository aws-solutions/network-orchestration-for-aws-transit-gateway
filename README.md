# Serverless Transit Network Orchestrator

**[🚀Solution Landing Page](https://docs.aws.amazon.com/solutions/latest/serverless-transit-network-orchestrator/welcome.html)** | **[🚧Feature request](https://github.com/aws-solutions/serverless-transit-network-orchestrator/issues/new?assignees=&labels=feature-request%2C+enhancement&template=feature_request.md&title=)** | **[🐛Bug Report](https://github.com/aws-solutions/serverless-transit-network-orchestrator/issues/new?assignees=&labels=bug%2C+triage&template=bug_report.md&title=)** | **[📜Documentation Improvement](https://github.com/aws-solutions/serverless-transit-network-orchestrator/issues/new?assignees=&labels=document-update&template=documentation_improvements.md&title=)**

_Note: For any relevant information outside the scope of this readme, please refer to the solution landing page and implementation guide._

## Table of content

- [Solution Overview](#solution-overview)
- [Architecture](#architecture)
- [Installation](#installing-pre-packaged-solution-template)
  - [Parameters](#parameters-for-hub-template)
- [Customization](#customization)
  - [Setup](#setup)
  - [Unit Test](#unit-test)
  - [Build](#build)
  - [Deploy](#deploy)
- [Tags used by STNO](#tags-used-by-stno)
- [Migration path](#migration-path-v2---v3)
- [File Structure](#file-structure)
- [License](#license)
- [Operational Metrics](#collection-of-operational-metrics)

## Solution overview

The Serverless Transit Network Orchestrator (STNO) solution adds automation to AWS Transit Gateway. This solution provides the tools necessary to automate the process of setting up and managing transit networks in distributed AWS environments. A web interface is created to help control, audit, and approve (transit) network changes. STNO supports both AWS Organizations and standalone AWS account types.

Serverless Transit Network Orchestrator version 2.0 supports AWS Transit Gateway inter-Region peering and Amazon VPC prefix lists. Customers can establish peering connections between transit gateways to extend connectivity and build global networks spanning multiple AWS Regions. Version 2.0 also gives customers the ability to automatically register AWS Transit Gateway with Network Manager. This lets customers visualize and monitor their global network from a single dashboard rather than toggling between Regions from the AWS Console.

## Architecture

The solution follows hub-spoke deployment model and uses given workflow:

- An Amazon CloudWatch Events rule monitors Amazon VPC and subnet tags. To identify the VPCs (spoke accounts) for the solution to manage, tag the VPCs and the selected subnets within those VPCs.

- This tag change is sent to the hub account through an Amazon EventBridge bus.

- When the event is received in the hub account, an AWS Lambda function is initiated to start the Serverless Transit Network Orchestrator workflow.

- AWS Step Functions (Serverless Transit Network Orchestrator state machine) and Lambda process network requests from the spoke accounts and event details are stored in Amazon DynamoDB. You can approve requests automatically or manually.

<img src="./architecture.png" width="750" height="450">

## Installing pre-packaged solution template

- Deploy in the account you want to act as the hub: [aws-transit-network-orchestrator-hub.template](https://solutions-reference.s3.amazonaws.com/serverless-transit-network-orchestrator/latest/aws-transit-network-orchestrator-hub.template)
- Deploy in spoke accounts: [aws-transit-network-orchestrator-spoke.template](https://solutions-reference.s3.amazonaws.com/serverless-transit-network-orchestrator/latest/aws-transit-network-orchestrator-spoke.template)
- Deploy in AWS Organizations management account: [aws-transit-network-orchestrator-organization-role.template](https://solutions-reference.s3.amazonaws.com/serverless-transit-network-orchestrator/latest/aws-transit-network-orchestrator-organization-role.template)

_Note: All templates need to be deployed in the same preferred region_

#### Parameters for hub template

- **Principal Type**: Choose to provide list of accounts (comma separated) or AWS Organizations ARN
- **Account List or AWS Organizations ARN**: AWS account numbers eg. 123456789012 (comma separated) OR the ARN of an Organization
- **AllowListedRanges**: Comma separated list of CIDR ranges that allow to console to access the API. To allow all the entire internet, use 0.0.0.0/1,128.0.0.0/1
- **Console Login Information Email**: Cognito user email where the temporary password will be sent
- **Cognito Domain Prefix**: A unique string that becomes part of the URL of the Cognito Hosted UI for your console instance

_Note: You may leave rest of the parameters to default value. For more details on the parameters, please refer to the guide [here](https://docs.aws.amazon.com/solutions/latest/serverless-transit-network-orchestrator/deployment.html#step1)._

#### Parameters for spoke template

- **Network (Hub) Account**: The account ID for the hub account, where AWS Transit Gateway resides

#### Parameters for organization-role template

- **Network (Hub) Account**: The account ID for the hub account, where AWS Transit Gateway resides

## Customization

The steps given below can be followed if you are looking to customize the solution or extend the solution with newer capabilities.

### Setup

- Python Prerequisite: python=3.9 | pip3=21.3.1
- Javascript Prerequisite: node=v14.17.0 | npm=8.5.3

Clone the repository and make desired code changes.

```
git clone aws-solutions/serverless-transit-network-orchestrator
```

_Note: Following steps have been tested under above pre-requisites_

### Unit Test

Run unit tests to make sure added customization passes the tests.

```
cd ./deployment
chmod +x ./run-unit-tests.sh
./run-unit-tests.sh
```

_✅ Ensure all unit tests pass. Review the generated coverage report_

### Build

To build your customized distributable follow given steps.

_Note: For PROFILE_NAME, substitute the name of an AWS CLI profile that contains appropriate credentials for deploying in your preferred region_

- Create an S3 bucket with the format 'MY-BUCKET-<aws_region>'. The solution's CloudFormation template will expect the source code to be located in this bucket. <aws_region> is where you are testing the customized solution.

You can use the following commands to create this bucket

```
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account --profile <PROFILE_NAME>)
REGION=$(aws configure get region --profile <PROFILE_NAME>)
BUCKET_NAME=stno-$ACCOUNT_ID-$REGION
aws s3 mb s3://$BUCKET_NAME/

# Default encryption:
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

# Enable public access block:
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

- Configure the solution name, version number and bucket name

```
SOLUTION_NAME=serverless-transit-network-orchestrator
DIST_OUTPUT_BUCKET=stno-$ACCOUNT_ID
VERSION=custom001
```

- Build the distributable using build-s3-dist.sh

```
cd ./deployment
chmod +x ./build-s3-dist.sh
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION
```

_✅ All assets are now built. You should see templates under deployment/global-s3-assets and other artifacts (console and lambda binaries) under deployment/regional-s3-assets_

### Deploy

Deploy the distributable to an Amazon S3 bucket in your account

```
aws s3 ls s3://$BUCKET_NAME  # should not give an error
cd ./deployment
aws s3 cp global-s3-assets/  s3://$BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --expected-bucket-owner $ACCOUNT_ID --profile <PROFILE_NAME>
aws s3 cp regional-s3-assets/  s3://$BUCKET_NAME/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --expected-bucket-owner $ACCOUNT_ID --profile <PROFILE_NAME>
```

_✅ All assets are now staged on your S3 bucket. You or any user may use S3 links for deployments_

- If using STNO with AWS Organizations, make sure that AWS RAM (Resources Access Manager) sharing is enabled in the management account (Refer [here](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services.html#orgs_how-to-enable-disable-trusted-access)).

- (Optional) If using AWS Organizations, if you want STNO to add tags with the account name/OU, and if the STNO account is not a [Delegated Administrator for any AWS service](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services_list.html), log into the management account and create a CloudFormation stack using the `aws-transit-network-orchestrator-organization-role.template` link from your bucket.

- Deploy the Serverless Transit Network Orchestrator to your account by launching a new AWS CloudFormation stack using the `aws-transit-network-orchestrator-hub.template` and `aws-transit-network-orchestrator-spoke.template` links from your S3 bucket.

## Tags used by STNO

### Creating Transit Gateway attachments

To attach a VPC to the Transit Gateway, the following tags are required. The tags should ideally be applied on the VPC first, and then the subnets, though STNO will also work if the tags are applied the other way around.

---

| Resource | Tag key        | Tag value                                                        |
| -------- | -------------- | ---------------------------------------------------------------- |
| VPC      | Associate-with | The name (not ID) of the TGW route table to associate with.      |
| VPC      | Propagate-to   | A comma separated list of TGW route table names to propagate to. |
| Subnet   | Attach-to-tgw  | _No tag value is required_                                       |

The `Attach-to-tgw` tag defines which subnet is used to attach to the Transit Gateway. The Attach-to-tgw tag needs to be applied to a subnet in every availability zone in the VPC. For example, if a VPC spans 2 AZs, 2 subnets (one in each AZ) needs to be tagged. If the VPC spans 3 AZs, 3 subnets (one in each AZ) would need to be tagged. Two subnets in the same AZ should not be tagged, if that happens by accident, the STNO event will fail with a `DuplicateSubnetsInSameZone` error, and the tag will need to be removed.

After the VPCs and subnets are tagged, the VPC/Subnets will have tags added starting with STNOStatus with details on whether the request was successful.

### Tags applied to the Transit Gateway Attachment

When STNO creates a Transit Gateway attachment, it creates the following tags for the attachment:

- **Name**: This is set to either <VPC Name>, or (if AWS Organizations integration is enabled) <OU Path>/<Account Name>: <VPC Name>
- **account-name**: (only with AWS Organizations integration) The name of the account associated with the attachment.
- **account-ou**: (only with AWS Organizations integration) The AWS Organizations OU path, starting and ending with a slash.
- All the tags listed in the STNO-Hub CloudFormation stack comma separated Parameter `ListOfVpcTagsForAttachment` is copied from the VPC being attached, if they exist.

### Transit Gateway Route Approvals

The only mandatory tag in the Transit Gateway Route Tables is the Name tag, which is set to the name of the Transit Gateway route table.

If an approval is required before a VPC can attach to the Route Table, the following tag can be applied:

- **ApprovalRequired**: One of: `Yes | No | Conditional`

This is the behavior for each of the ApprovalRequired values:

- **No**: No manual approval is required. If all Route Tables that a VPC associates to and propagates with does not need approval, then the attachment is auto-approved.
- **Yes**: Manual approval is always required, whether it is associated or propagated to this route table.
- **Conditional**: Uses the rules defined below. Unmatched rules default to manual approved.

If ApprovalRequired is set to Conditional, the following additional tags can be defined:

---

| Tag key                                               | Required?            | Default          | Description                                                                                                                                                                                                                                                                                   | Tag Values accepted                  |
| ----------------------------------------------------- | -------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `ApprovalRule-Default-Association`                    | No                   | ApprovalRequired | The action to take for Associate-with route tables if none of the rules below match.                                                                                                                                                                                                          | Reject \| Accept \| ApprovalRequired |
| `ApprovalRule-Default-Propagation`                    | No                   | ApprovalRequired | The action to take for Propagate-to route tables if none of the rules below match.                                                                                                                                                                                                            | Reject \| Accept \| ApprovalRequired |
| `ApprovalRule-01-InOUs` or `ApprovalRule-01-NotInOUs` | If rule is required. | No default       | A comma separated list of OU paths. If the tag key contains `InOUs`, the rule will match if the account is in one of these OUs. If the tag key contains `NotInOUs`, the rule will match if the account is not in any of the specified OUs. Starting/ending the path with a slash is optional. | /List/,/Of/,/OU/,/Paths/             |
| `ApprovalRule-01-Association`                         | No                   | ApprovalRequired | The approval action to take for a VPC that associates with this route table if the InOUs or NotInOUs check matches.                                                                                                                                                                           | Reject \| Accept \| ApprovalRequired |
| `ApprovalRule-01-Propagation`                         | No                   | ApprovalRequired | The approval action to take for a VPC that propagates to this route table if the InOUs or NotInOUs check matches.                                                                                                                                                                             | Reject \| Accept \| ApprovalRequired |

Additional rule numbers can be added (for example ApprovalRule-02-\*), and the rule numbers needs to be sequential (01, 02, 03, etc). As long as the limit of 50 tags per Transit Gateway Route Table resource is not reached, as many rules can be added as needed (realistically around ~15-20 rules). If the tag limit of 50 is close to being reached, rules with an “ApprovalRequired” value can be removed, as that is the default.

For a conditional approval rule, if any of the route tables associated/propagated to a VPC attachment request triggers a `Reject` rule, the request will be auto-rejected regardless if there is a `ApprovalRequired` tag. Otherwise, if any of the route tables rules results in `ApprovalRequired`, the request will go through a manual approval even if all other route tables are set to `Accept`. Otherwise, if all route tables rules result in Accept or has an `ApprovalRequired` tag key set to no., then the request is auto-`Accept`ed.

## Migration path (v2 -> v3)

### Hub template

We will deploy v3 template along side v2 template and delete v2 template later.

- Download the v3 hub template. Make following modification under the _mappings_ section \*\* and save the file

  ```
  NotificationConfiguration:
      SNS:
        DisplayName: "AWS Transit Network Change Approval Notification for v3"
        TopicName: AWS-Transit-Network-Approval-Notifications-v3
  EventBridge:
      Bus:
        Name: "STNO-EventBridge-v3"
  ```

- Deploy the template saved in the first step in the same region as older deployment

  For parameters review, **Transit Gateway Settings**:

  - Provide the existing transit gateway id: copy the transit gateway id created by v2 deployment
  - Provide the existing global network id: copy the global network created by v2 deployment (can be left blank if v2 did not create global network)

  _You would notice few parameters removed from v3 hub template. It is safe to ignore those parameters. For rest, please copy the value you entered for v2 deployment._

- Migrate DynamoDB table to retain historical network-change events

  For the purpose of the instructions we will consider old_table as the table created by older STNO deployment and new_table as the table created by the newer (v3.0.0) STNO deployment

  - Create DynamoDB backup for old table

    - Go to [DynamoDB console](https://us-east-1.console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables). You should see the old_table deployed by the old deployment. Click <StackName>-DynamoDBTable-<XXXX>
    - Select _Backups_ tabs > _Create backup_ > _Create on-demand backup_
    - Under _Backup settings_, select _Customize settings_ > _Backup with DynamoDB_
    - Give a _Backup name_ and hit _Create backup_

  - Restore DynamoDB backup to new table
    - Delete the DynamoDB table created by the new deployment as we will be restoring from old table
    - Go to the old*table. You should see the backup created earlier under table \_Backups*. Select the backup > click _Restore_
    - For _Name of restored table_, \** give same name to the new_table as deployed by the v3.0.0 template. Table name can be found from template *Outputs\* section as well
    - Select _Restore the entire table_ > _Same Region_
    - Under encryption settings choose _Owned by Amazon DynamoDB_ and hit _Restore_
    - new_table should be restored with the old_table backup in under 10 minutes
    - You should now see all the historical network-change events on the solution UI

_✅ Now it is safe to delete the older STNO hub deployment_

### Spoke template

For spoke template we can follow CloudFormation stack update process.

- Download the v3 spoke template. Make following modification under the _mappings_ section \*\* and save the file
  ```
  EventBridge:
      Bus:
        Name: "STNO-EventBridge-v3" # should be same as hub template
  ```
- Go to [CloudFormation console](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#) and select to older v2 deployment
- Click _Update_ > _Replace current template_ > _Upload a template file_ and select the template saved in Step 1.
- Click _Next_ > Select _I acknowledge that AWS CloudFormation might create IAM resources with custom names_ > _Update Stack_
- Template update should be complete in under one minute

_✅ At this point we have successfully migrated to STNO v3.0.0_

## File structure

AWS Serverless Transit Network Orchestrator solution consists of:

- solution templates to provision needed AWS resources
- lambda microservices to implement solution functional logics
  - custom_resource: handle cfn custom resource CRUD
  - state_machine: handle solution's core state machine
  - tgw_peering: handle solution transit gateway peering functionality
- ui to deploy solution ui components

<pre>
|-.github
|-architecture.png                    [ architecture diagram ]
|-deployment/    
  |-manifest-generator                [ generates manifest files for solution ui ]                 
  |-stno-hub.template                 [ hub template, provisions transit gateway in hub account ]
  |-stno-spoke.template               [ spoke template, onboards child accounts on the solution ]  
  |-stno-organization-role.template   [ role template, deploys in management account ]
  |-build-s3-dist.sh                  [ script to build solution microservices ]
  |-run-unit-test.sh                  [ script to run unit tests ]
|-source/
  |-lambda/                           [ solution microservices ]  
    |-microservices                   [ custom_resource, state_machine, tgw_peering ]
      |-__tests__                     [ unit tests ]
      |-lib                           [ microservice helper modules ]
      |-index.py                      [ entry point for lambda function ]
    |-requirements.txt                [ production dependencies for the microservices ]
    |-testing_requirements.txt            [ dev dependencies for the microservices ]
    |-pytest.ini                      [ configuration file for running pytest ]
    |-.pylintrc                       [ configuration file for linting source code ]
    |-.coveragerc                     [ configuration file for coverage reported ]
  |-ui                                [ solution ui components ] 
|-additional_files                    [ CODE_OF_CONDUCT, NOTICE, LICENSE, sonar-project.properties etc.]
</pre>

## License

See license [here](./LICENSE.txt)

## Collection of operational metrics

This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. For more information, including how to disable this capability, please see the [implementation guide](https://docs.aws.amazon.com/solutions/latest/serverless-transit-network-orchestrator/operational-metrics.html).

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

```
http://www.apache.org/licenses/LICENSE-2.0
```

or in the ["license"](./LICENSE.txt) file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
