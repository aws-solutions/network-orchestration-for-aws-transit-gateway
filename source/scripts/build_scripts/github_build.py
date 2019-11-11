#!/usr/bin/env python
import os
import shutil


def make_dir(directory):
    # if exist skip else create dir
    try:
        os.stat(directory)
        print("\n Directory {} already exist... skipping".format(directory))
    except:
        print("\n Directory {} not found, creating now...".format(directory))
        os.mkdir(directory)


def remove_dir(directory):
    # if does not exist skip else remove dir
    try:
        os.stat(directory)
        print("\n Directory {} already exist, deleting open-source directory".format(directory))
        shutil.rmtree(directory)
    except:
        print("\n Directory {} not found... nothing to delete".format(directory))


def copy_tree(function_path, output_path, github_exclude):
    orig_path = os.getcwd()
    os.chdir(function_path)
    src_dir = 'source'
    shutil.copytree(src_dir, output_path, ignore=shutil.ignore_patterns(*github_exclude))


def move_files(source, destination):
    files = os.listdir(source)
    os.chdir(source)
    for file in files:
        if '.' in file and '.py' not in file:
            shutil.move(file, destination)


if __name__ == "__main__":
    # if condition changes the path this script runs from command line 'solution-root$ python source/scripts/build_scripts/github_build.py'
    if 'scripts' not in os.getcwd():
        os.chdir('./source/scripts')
    # Cleanup if the open-source directory exist
    remove_dir('../../deployment/open-source')

    # Ignore patterns
    github_exclude = ('*.pyc', '.*', '*.egg-info', 'scratch*', 'github*', '__pycache__*', 'netaddr',
                      'dist-info', 'jinja2', 'simplejson', 'markupsafe', 'yaml', 'yorm', 'parse.py')

    # Create Github folder assets
    function_path = '../../'
    output_path = 'deployment/open-source/source'
    copy_tree(function_path, output_path, github_exclude)
    make_dir('deployment/open-source/deployment')

    # Move non-python files outside source folder
    source = 'deployment/open-source/source'
    destination = '../'
    move_files(source, destination)