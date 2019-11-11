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

# Copy ui files to regional-s3-assets and zip them
echo "pwd"
pwd
echo "ls -al"
ls -al
echo "== cp -R $source_dir/ui $build_dist_dir/"
cp -R $source_dir/ui $build_dist_dir/
echo "== mkdir -p $build_dist_dir/graphql"
mkdir -p $build_dist_dir/graphql
echo "== copy graphql files to $build_dist_dir/graphql"
echo "== cp -R $source_dir/ui/src/graphql/schema.graphql $source_dir/ui/src/graphql/resolver $source_dir/ui/src/graphql/function $build_dist_dir/graphql"
cp -R $source_dir/ui/src/graphql/schema.graphql $source_dir/ui/src/graphql/resolver $source_dir/ui/src/graphql/function $build_dist_dir/graphql
echo "== cd $build_dist_dir/ui/"
cd $build_dist_dir/ui/ 
echo "== [ -e node_modules ] && rm -rf node_modules "
[ -e node_modules ] && rm -rf node_modules 
echo "== npm install"
npm install
echo "rm package-lock.json"
rm package-lock.json
echo "== zip -q -r9 ../aws-transit-network-orchestrator-console.zip ../ui"
zip -q -r9 ../aws-transit-network-orchestrator-console.zip ../ui
echo "pwd"
pwd
echo "ls -al"
ls -al

# Build console files
[ -e build ] && rm -r build 
echo "== npm run build"
npm run build
cp -R ./build ../console
echo "== ls -al ../console"
ls -al ../console
echo "== cd ../../.. && rm -rf $build_dist_dir/ui"
cd ../../.. && rm -rf $build_dist_dir/ui
echo "pwd"
pwd
echo "ls -al"
ls -al

# Generate console manifest and add it to aws-transit-network-orchestrator-cr.zip
echo "== cd $template_dir/manifest-generator"
cd $template_dir/manifest-generator
echo "== [ -e node_modules ] && rm -rf node_modules"
[ -e node_modules ] && rm -rf node_modules
echo "== npm install"
npm install
node app.js --target "$build_dist_dir/console" --output "$build_dist_dir/console-manifest.json"
echo "== rm package-lock.json"
rm package-lock.json
echo "== ls -al $build_dist_dir/console"
ls -al $build_dist_dir/console
echo "Add console-manifest.json to aws-transit-network-orchestrator-cr.zip file" 
echo "cd $build_dist_dir && zip -rv ./aws-transit-network-orchestrator-cr.zip ./console-manifest.json"
cd $build_dist_dir && zip -rv ./aws-transit-network-orchestrator-cr.zip ./console-manifest.json
echo "return to root directory: cd ../.."
cd ../..

# Copy template files to global-s3-assets directory
echo "cp -f $template_dir/aws-transit-network-orchestrator-hub.template $template_dist_dir"
cp -f $template_dir/aws-transit-network-orchestrator-hub.template $template_dist_dir
echo "cp -f $template_dir/aws-transit-network-orchestrator-spoke.template $template_dist_dir"
cp -f $template_dir/aws-transit-network-orchestrator-spoke.template $template_dist_dir

# Replace source code s3 bucket name with real value
echo -e "\n >> Updating code source bucket in the template with $1"
replace="s/%DIST_BUCKET_NAME%/$1/g"
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template

# Replace solution name with real value
echo -e "\n >> Updating solution name in the template with $2"
replace="s/%SOLUTION_NAME%/$2/g"
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template

# Replace version variable with real value
echo -e "\n >> Updating version number in the template with $3"
replace="s/%VERSION%/$3/g"
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-hub.template
echo "sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template"
sed -i -e $replace $template_dist_dir/aws-transit-network-orchestrator-spoke.template

