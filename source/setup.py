#!/usr/bin/env python
from __future__ import unicode_literals
from setuptools import setup, find_packages

#Use "source/scripts/pip_install_dependencies.py" to install dependencies

tests_requires = [
    'pytest-mock == 1.10.4',
    'pytest-runner == 4.4',
    'pytest == 4.4.1'
]

setup(
    name='aws-serverless-transit-network-orchestrator',
    version='1.0.0',
    description='AWS Serverless Transit Networl Orchestrator',
    author='Lalit G.',
    url='https://github.com/awslabs/aws-serverless-transit-network-orchestrator',
    packages=find_packages(exclude=("tests", "tests.*")),
    license="Amazon",
    zip_safe=False,
    test_suite="tests",
    tests_require=tests_requires,
    setup_requires=['pytest-runner'],
    classifiers=[
        "Programming Language :: Python :: 3.7"
    ],
)