"""
This module loads and parses the command line arguments.
"""

import argparse
import framework
import os
import sys
import yaml

# Directories
TOP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = os.path.join(TOP_DIR, "templates")


def process_arguments(arguments):
    """
    This function process the arguments which are passed to noobaa-sa-infra

    Args:
        arguments (list): List of arguments

    """
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--conf", action="append", default=[])

    # Create a mutually exclusive group for nsfs and db
    group = parser.add_mutually_exclusive_group()

    # Add the options to the mutually exclusive group
    group.add_argument(
        "--nsfs",
        action="store_true",
        help="""Install NooBaa Standalone with NSFS""",
    )
    group.add_argument(
        "--db",
        action="store_true",
        help="""Install NooBaa Standalone with db""",
    )

    args, unknown = parser.parse_known_args(args=arguments)
    nsfs_installation = args.nsfs
    db_installation = args.db

    # Check if neither nsfs nor db is specified
    if not (nsfs_installation or db_installation):
        parser.error("One of --nsfs or --db must be specified.")

    # load nsfs_installation and db_installation values to config
    framework.config.ENV_DATA["nsfs_installation"] = nsfs_installation
    framework.config.ENV_DATA["db_installation"] = db_installation

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
