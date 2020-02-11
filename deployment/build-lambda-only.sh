#!/bin/bash

# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name trademarked-solution-name version-code
#
# Paramenters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions my-solution v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - trademarked-solution-name: name of the solution for consistency
#
#  - version-code: version of the package

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

# Get reference for all important folders
 template_dir="$PWD"
 template_dist_dir="$template_dir/global-s3-assets"
 build_dist_dir="$template_dir/regional-s3-assets"
 source_dir="$template_dir/../source"

 echo "------------------------------------------------------------------------------"
 echo "[Init] Clean old dist, node_modules and bower_components folders"
 echo "------------------------------------------------------------------------------"
 echo "rm -rf $template_dist_dir"
 rm -rf $template_dist_dir
 echo "mkdir -p $template_dist_dir"
 mkdir -p $template_dist_dir
 echo "rm -rf $build_dist_dir"
 rm -rf $build_dist_dir
 echo "mkdir -p $build_dist_dir"
 mkdir -p $build_dist_dir

# Create zip file for AWS Lambda functions
echo -e "\n >> Creating all lambda functions for Serverless Transit Network Orchestrator Solution"
python source/scripts/build_scripts/lambda_build.py custom_resource_lambda state_machine_lambda
python $source_dir/scripts/build_scripts/lambda_build.py custom_resource_lambda state_machine_lambda

echo -e "\n >> Cleaning up the tests and ui folder from the lambda zip files \n"
zip -d $build_dist_dir/aws-transit-network-orchestrator-cr.zip tests/* ui/*
zip -d $build_dist_dir/aws-transit-network-orchestrator-sm.zip tests/* ui/*

