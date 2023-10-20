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

[ "$DEBUG" == 'true' ] && set -x
set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

# function to print headers
function headline(){
  echo "------------------------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------------------------"
}


headline "[Init] Setting up paths"
template_dir="$PWD"
template_dist_dir="$template_dir/global-s3-assets"
build_dist_dir="$template_dir/regional-s3-assets"
source_dir="$template_dir/../source"
lambda_dir="$source_dir/lambda"


headline "[Init] Clean old folders"
rm -rf $template_dist_dir
mkdir -p $template_dist_dir
rm -rf $build_dist_dir
mkdir -p $build_dist_dir

headline "[Init] Clean python generated files & folders"
cd $lambda_dir
find . -iname ".venv" -type d | xargs rm -rf
find . -iname "__pycache__" -type d | xargs rm -rf
find . -iname "dist" -type d | xargs rm -rf
find . -type f -name ".pytest_cache" -delete
find . -type f -name ".coverage" -delete

headline "[Init] Initiating virtual environment"
python3 -m venv .venv --upgrade-deps
source .venv/bin/activate
pip3 install -r requirements.txt

headline "[Build] Build cognito-trigger function"
echo "cd $source_dir/cognito-trigger"
cd $source_dir/cognito-trigger
echo "npm run build:all"
npm run build:all
cp -R "dist/cognito-trigger.zip" $build_dist_dir

headline "[Build] Lambda zips for STNO Solution"
cd $lambda_dir
for microservices in */ ; do
  echo "building $microservices"
  microservice_name=$(basename $microservices)
  cd $lambda_dir/$microservice_name
  mkdir -p dist/$microservice_name
  rsync -aq $lambda_dir/.venv/lib/python3.11/site-packages/ ./dist/
  cp -R lib __init__.py main.py ./dist/$microservice_name/
  cd dist
  zip -rq "$microservice_name.zip" .
  cp -R "$microservice_name.zip" $build_dist_dir
  rm -rf $lambda_dir/$microservice_name/dist
done
deactivate

headline "[Stage] Copy ui files to regional-s3-assets, build console and zip"
cp -R $source_dir/ui $build_dist_dir/
mkdir -p $build_dist_dir/graphql
cp -R $source_dir/ui/src/graphql/schema.graphql $source_dir/ui/src/graphql/resolver $source_dir/ui/src/graphql/function $build_dist_dir/graphql
cd $build_dist_dir/ui/
[ -e node_modules ] && rm -rf node_modules 
npm ci
[ -e build ] && rm -r build 
npm run build
cp -R ./build ../console
cd ../../.. && rm -rf $build_dist_dir/ui

headline "[Build] Generate console manifest and add it to custom_resource.zip"
cd $template_dir/manifest-generator
[ -e node_modules ] && rm -rf node_modules
npm ci
node app.js --target "$build_dist_dir/console" --output "$build_dist_dir/console-manifest.json"
cd $build_dist_dir && zip -rq ./custom_resource.zip ./console-manifest.json
cd ../..

headline "[Stage] Copy templates to global-s3-assets directory"
cp -f $template_dir/network-orchestration-hub.template $template_dist_dir
cp -f $template_dir/network-orchestration-spoke.template $template_dist_dir
cp -f $template_dir/network-orchestration-organization-role.template $template_dist_dir
cp -f $template_dir/network-orchestration-hub-service-linked-roles.template $template_dist_dir
cp -f $template_dir/network-orchestration-spoke-service-linked-roles.template $template_dist_dir

# Find and replace bucket_name, solution_name, and version
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac OS
    # Replace source code s3 bucket name with real value
    replace="s/%DIST_BUCKET_NAME%/$1/g"
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template

    # Replace solution name with real value
    replace="s/%SOLUTION_NAME%/$2/g"
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template

    # Replace version variable with real value
    replace="s/%VERSION%/$3/g"
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i '' -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template
else
    # Other linux
    # Replace source code s3 bucket name with real value
    replace="s/%DIST_BUCKET_NAME%/$1/g"
    sed -i -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template

    # Replace solution name with real value
    replace="s/%SOLUTION_NAME%/$2/g"
    sed -i -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template

    # Replace version variable with real value
    replace="s/%VERSION%/$3/g"
    sed -i -e $replace $template_dist_dir/network-orchestration-hub.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke.template
    sed -i -e $replace $template_dist_dir/network-orchestration-organization-role.template
    sed -i -e $replace $template_dist_dir/network-orchestration-hub-service-linked-roles.template
    sed -i -e $replace $template_dist_dir/network-orchestration-spoke-service-linked-roles.template
fi
