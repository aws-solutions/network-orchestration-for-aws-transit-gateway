#!/bin/bash

[ "$DEBUG" == 'true' ] && set -x
set -e

source_dir="$PWD"
lambda_dir="$source_dir/lambda"

setup_python_env() {
  if [ -d "./.venv-test" ]; then
    echo "Reusing already setup python venv in ./.venv-test. Delete ./.venv-test if you want a fresh one created."
    return
  fi

  echo "Setting up python venv"
  python3 -m venv .venv-test
  echo "Initiating virtual environment"
  source .venv-test/bin/activate

  echo "Installing python packages"
  # install test dependencies in the python virtual environment
  pip3 install -r requirements-dev.txt
  pip3 install -r requirements.txt
  pipdeptree

  echo "deactivate virtual environment"
  deactivate
}

run_python_tests() {
  local component_path=$1

  echo "------------------------------------------------------------------------------"
  echo "[Test] Run python unit test with coverage for $component_path"
  echo "------------------------------------------------------------------------------"
  cd $component_path

  if [ "${CLEAN:-true}" = "true" ]; then
        rm -fr .venv-test
    fi

  setup_python_env

  echo "Initiating virtual environment"
  source .venv-test/bin/activate

  coverage_report_path="$source_dir/lambda/coverage.xml"
  echo "coverage report path set to $coverage_report_path"

  # Use -vv for debugging
  coverage run -m pytest && coverage xml && coverage report -m

    # The pytest --cov with its parameters and .coveragerc generates a xml cov-report with `coverage/sources` list
    # with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
    # absolute paths for source directories, this substitution is used to convert each absolute source directory
    # path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' -e "s,<source>.*</source>,<source>source/lambda</source>,g" $coverage_report_path
    else
      sed -i -e "s,<source>.*</source>,<source>source/lambda</source>,g" $coverage_report_path
    fi

  echo "deactivate virtual environment"
  deactivate

  if [ "${CLEAN:-true}" = "true" ]; then
    rm -fr .venv-test
    rm .coverage
    rm -fr .pytest_cache
    rm -fr __pycache__ test/__pycache__
  fi
}

run_javascript_tests() {
  local component_path=$1

  echo "------------------------------------------------------------------------------"
  echo "[Test] Run javascript unit test with coverage for $component_path"
  echo "------------------------------------------------------------------------------"

  cd $component_path
  npm install
  npm run test # run with coverage, make sure to disable watch mode
}

# Test the WebUI project
run_javascript_tests $source_dir/ui || true

# Test the cognito-trigger project
run_javascript_tests $source_dir/cognito-trigger || true

# Test the attached Lambda functions
run_python_tests $source_dir/lambda

# Return to the source/ level
cd $source_dir