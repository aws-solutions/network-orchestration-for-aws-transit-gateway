# AWS Serverless Transit Network Orchestrator
The AWS Serverless Transit Network Orchestrator is a reference implementation that ... 
 
## Getting Started 
To get started with the AWS Serverless Transit Network Orchestrator, please review the solution documentation. https://aws.amazon.com/solutions/serverless-transit-network-orchestrator
 
## Running unit tests for customization 
* Clone the repository, then make the desired code changes 
* Next, run unit tests to make sure added customization passes the tests 
``` 
cd ./deployment 
chmod +x ./run-unit-tests.sh  \n 
./run-unit-tests.sh \n 
``` 
 
## Building distributable for customization 
* Configure the bucket name of your target Amazon S3 distribution bucket 
``` 
export SOLUTION_NAME=my-solution-name # name of the solution
export DIST_OUTPUT_BUCKET=my-bucket-name # bucket where customized code will reside 
export VERSION=my-version # version number for the customized code 
``` 
_Note:_ You would have to create an S3 bucket with prefix 'my-bucket-name-<aws_region>'; aws_region is where you are testing the customized solution. Also, the assets  in bucket should be publicly accessible 
 
* Now build the distributable: 
``` 
chmod +x ./build-s3-dist.sh \n 
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION \n 
``` 
 
* Deploy the distributable to an Amazon S3 bucket in your account. _Note:_ you must have the AWS Command Line Interface installed. 
``` 
aws s3 cp ./dist/ s3://my-bucket-name/serverless-transit-network-orchestrator/<my-version>/ --recursive --exclude "*" --include "*.template" --include "*.json" --acl bucket-owner-full-control --profile aws-cred-profile-name \n 
aws s3 cp ./dist/ s3://my-bucket-name-<aws_region>/serverless-transit-network-orchestrator/<my-version>/ --recursive --exclude "*" --include "*.zip" --acl bucket-owner-full-control --profile aws-cred-profile-name \n 
``` 
 
* Get the link of the serverless-transit-network-hub.template uploaded to your Amazon S3 bucket. 
* Deploy the AWS Serverless Transit Network Orchestrator to your account by launching a new AWS CloudFormation stack using the link of the serverless-transit-network-hub.template. 
 
*** 
 
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved. 
 
Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at 
 
    http://www.apache.org/licenses/LICENSE-2.0 
 
or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License. 
 