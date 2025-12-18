#!/bin/bash

[ "$DEBUG" == 'true' ] && set -x
set -e

source_dir="$PWD"
lambda_dir="$source_dir/lambda"

# run unit test for cognito-trigger package
cd ./cognito-trigger
npm ci
npm run test

# run unit test for ui package
cd ../ui
npm ci
npm run test

# run unit test for lambda package
cd ../lambda
poetry install
poetry run coverage run -m pytest && \
poetry run coverage xml && \
poetry run coverage report

# The pytest --cov with its parameters generates a xml cov-report with `coverage/sources` list
# with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
# absolute paths for source directories, this substitution is used to convert each absolute source directory
# path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
coverage_report_path="$lambda_dir/coverage.xml"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e "s,<source>.*</source>,<source>source/lambda</source>,g" $coverage_report_path
else
  sed -i -e "s,<source>.*</source>,<source>source/lambda</source>,g" $coverage_report_path
fi