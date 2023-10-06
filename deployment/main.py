import argparse
import framework
import os
import pytest
import sys
import yaml


# Directories
TOP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = os.path.join(TOP_DIR, "noobaa-sa-ci", "templates")


def process_arguments(arguments):
    """
    This function process the arguments which are passed to noobaa-sa-infra

    Args:
        arguments (list): List of arguments

    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--conf", action="append", default=[])

    args, unknown = parser.parse_known_args(args=arguments)
    load_config(args.conf)


def load_config(config_files):
    """
    This function load the config files in the order defined in config_files
    list.

    Args:
        config_files (list): config file paths

    """
    for config_file in config_files:
        with open(os.path.abspath(os.path.expanduser(config_file))) as file_stream:
            custom_config_data = yaml.safe_load(file_stream)
            framework.config.update(custom_config_data)


def load_args(argv=None):
    """
    This function loads the arguments
    """
    arguments = argv or sys.argv[1:]
    process_arguments(arguments)
    framework.config.ENV_DATA["template_dir"] = TEMPLATE_DIR


def noobaa_sa_install():
    """
    Installs NooBaa Standalone with pytest
    """
    load_args()
    return pytest.main(['-v', 'tests/deployment/test_deployment.py'])