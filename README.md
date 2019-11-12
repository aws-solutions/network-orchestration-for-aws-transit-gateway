# Serverless Transit Network Orchestrator
The Serverless Transit Network Orchestrator (STNO) solution adds automation to AWS Transit Gateway. This solution provides the tools necessary to automate the process of setting up and managing transit networks in distributed AWS environments. A web interface is created to help control, audit, and approve (transit) network changes. STNO supports both AWS Organizations and standalone AWS account types.
 
## Getting Started 
To get started with the Serverless Transit Network Orchestrator, please review the solution documentation. https://aws.amazon.com/solutions/serverless-transit-network-orchestrator
 
## Running unit tests for customization 
* Clone the repository, then make the desired code changes 
* Next, run unit tests to make sure added customization passes the tests 
``` 
cd ./deployment 
chmod +x ./run-unit-tests.sh
./run-unit-tests.sh
``` 
 
## Building distributable for customization 
* Configure the solution name, version number and bucket name of your target Amazon S3 distribution bucket 
``` 
export SOLUTION_NAME=my-solution-name # name of the solution
export DIST_OUTPUT_BUCKET=my-bucket-name # bucket where customized code will reside 
export VERSION=my-version # version number for the customized code 
``` 
_Note:_ You would have to create an S3 bucket with prefix 'my-bucket-name-<aws_region>'; aws_region is where you are testing the customized solution. Also, the assets  in bucket should be publicly accessible 
 
* Now build the distributable: 
``` 
chmod +x ./build-s3-dist.sh
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION
``` 
 
* Deploy the distributable to an Amazon S3 bucket in your account. _Note:_ you must have the AWS Command Line Interface installed. 
``` 
aws s3 cp deployment/global-s3-assets/  s3://$TEMPLATE_OUTPUT_BUCKET/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --profile aws-cred-profile-name 
aws s3 cp deployment/regional-s3-assets/ s3://$BUILD_OUTPUT_BUCKET/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --profile aws-cred-profile-name
``` 
 
* Get the link of the aws-transit-network-orchestrator-hub.template and aws-transit-network-orchestrator-spoke.template uploaded to your Amazon S3 bucket. 
* Deploy the Serverless Transit Network Orchestrator to your account by launching a new AWS CloudFormation stack using the link of the aws-transit-network-orchestrator-hub.template and aws-transit-network-orchestrator-spoke.template
 
*** 
 
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved. 
 
Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at 
 
    http://www.apache.org/licenses/LICENSE-2.0 
 
or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License. 
 