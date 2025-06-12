# Network Orchestration for AWS Transit Gateway - Lambda Components

This directory contains the AWS Lambda functions that power the Network Orchestration for AWS Transit Gateway solution. The solution is designed to automate and manage AWS Transit Gateway attachments and peering connections.

## Project Structure

The project is organized into the following main components:

```
source/lambda/
├── solution/                      # Main application code
│   ├── custom_resource/           # Custom resource handler for CloudFormation
│   │   ├── lib/                   # Helper libraries for custom resources
│   │   └── main.py                # Entry point for Custom Resource Lambda
│   ├── tgw_peering_attachment/    # Transit Gateway peering attachment handler
│   │   ├── lib/                   # Helper libraries for TGW peering
│   │   └── main.py                # Entry point for Tgw Peering Lambda
│   └── tgw_vpc_attachment/        # Transit Gateway VPC attachment handler
│       ├── lib/                   # Helper libraries for TGW VPC attachments
│       │   ├── clients/           # AWS service clients (EC2, DynamoDB, etc.)
│       │   ├── handlers/          # Business logic handlers
│       │   └── utils/             # Utility functions
│       └── main.py                # Entry point for the State Machine Lambda
├── tests/                         # Test suite
│   ├── custom_resource/           # Tests for custom resource module
│   ├── tgw_peering_attachment/    # Tests for TGW peering attachment module
│   └── tgw_vpc_attachment/        # Tests for TGW VPC attachment module
├── pyproject.toml                 # Poetry project configuration
├── poetry.lock                    # Poetry dependency lock file
├── poetry.toml                    # Poetry configuration
├── pytest.ini                     # Pytest configuration
├── .pylintrc                      # Configuration for the pylint code linter
└── README.md                      # This file
```

## Application Overview

This Python application is designed to orchestrate AWS Transit Gateway resources, providing automated management of:

1. **Transit Gateway VPC Attachments**: Handles the creation, configuration, and management of VPC attachments to Transit Gateways.
2. **Transit Gateway Peering Attachments**: Manages peering connections between Transit Gateways.
3. **Custom Resources**: Provides CloudFormation custom resources for integration with AWS CloudFormation.

## Installation Instructions

### Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Setting Up the Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/aws-solutions/network-orchestration-for-aws-transit-gateway.git
   cd source/lambda
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

   This will create a virtual environment and install all the required dependencies defined in `pyproject.toml`.

3. Activate the Poetry virtual environment:
   ```bash
   poetry shell
   ```

## Running Tests

The project uses pytest for testing. To run the tests:

1. Run tests:
   ```bash
   poetry run pytest
   ```

2. Run tests with coverage report:
   ```bash
   poetry run coverage run -m pytest
   ```

3. Run specific test modules:
   ```bash
   poetry run pytest tests/tgw_vpc_attachment/
   ```

4. Run tests with verbose output:
   ```bash
   poetry run pytest -v
   ```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
