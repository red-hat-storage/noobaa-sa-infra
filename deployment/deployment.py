import logging
import os
import re
import requests
import time
from datetime import datetime

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from common_ci_utils.command_runner import exec_cmd
from common_ci_utils.exceptions import (
    AggregateNodeStatusCheckFailed,
    ServiceRunningFailed,
    StorageStatusCheckFailed,
)
from common_ci_utils.file_system_utils import create_directory, set_permissions
from common_ci_utils.host_info import get_ip_address
from common_ci_utils.package_fetcher import download_rpm
from common_ci_utils.postgres_utils import enable_postgresql_version
from common_ci_utils.rpm_manager import install_rpm
from common_ci_utils.service_manager import is_service_running, start_service
from common_ci_utils.templating import Templating
from common_ci_utils.url_utils import get_html_content
from deployment.npm import NPM
from framework import config, exceptions

log = logging.getLogger(__name__)


class Deployment(object):
    """
    Noobaa SA deployment
    """

    def __init__(self):
        """
        Initializes the necessary variables needed for
        Noobaa Standalone Deployment
        """
        self.rpm_url = config.ENV_DATA.get("noobaa_sa", "")
        upstream = (
            config.DEPLOYMENT["upstream"] or
            config.DEPLOYMENT["upstream_rpm_s3_base_url"] in self.rpm_url
        )
        if config.DEPLOYMENT["downstream_rpm_base_url"] in self.rpm_url:
            upstream = False

        if upstream:
            self.username = None
            self.password = None
        else:
            self.username = config.DEPLOYMENT["rpm_auth_username"]
            self.password = config.DEPLOYMENT["rpm_auth_password"]
        if not self.rpm_url:
            if config.DEPLOYMENT["upstream"]:
                self.rpm_url = self.get_latest_upstream_rpm()
            else:
                self.rpm_url = self.get_latest_downstream_rpm()


    def install_rpm(self):
        """
        Install rpm
        """
        rpm_path = download_rpm(self.rpm_url, self.username, self.password)
        install_rpm(rpm_path=rpm_path)


    def get_latest_downstream_rpm(self):
        """
        Fetch latest downstream RPM for Noobaa SA
        """
        # Parse the HTML content
        url = urljoin(
            config.DEPLOYMENT["downstream_rpm_base_url"],
            config.DEPLOYMENT["downstream_rpm_artifactory_path"]
        )
        html_content = get_html_content(url, self.username, self.password)
        soup = BeautifulSoup(html_content, 'html.parser')
        latest_package = None
        latest_date = None

        # Find all <a> tags within the <pre> tag
        for a_tag in soup.find_all('pre')[1].find_all('a'):
            href = a_tag.get('href')
            text = a_tag.next_sibling.strip()
            # Check if the href contains 'noobaa-core'
            if 'noobaa-core' in href and f"el9" in href:
                # Extract the date from the text
                date_str = ' '.join(text.split()[:2])
                date_obj = datetime.strptime(date_str, '%d-%b-%Y %H:%M')
                # Update the latest package and date if this one is newer
                if latest_date is None or date_obj > latest_date:
                    latest_date = date_obj
                    latest_package = href
        rpm_base_url = urljoin(url, latest_package)
        all_rpms_html = get_html_content(rpm_base_url, self.username, self.password)
        soup = BeautifulSoup(all_rpms_html, 'html.parser')
        regex = self.get_rpm_pattern()
        rpm_name = soup.find('a', href=regex)
        if rpm_name:
            package_url = rpm_name['href']
            return urljoin(rpm_base_url, package_url)
        else:
            raise exceptions.rpmNotFoundError(
                f"noobaa-core RPM not found in URL: {package_url}!"
            )


    def get_rpm_pattern(self):
        """
        Get rendered regexp pattern for RPM

        Returns:
            re.Pattern: to match RPM with
        """
        formatted_pattern_string = config.DEPLOYMENT['rpm_pattern'].format(
            rhel_version=config.DEPLOYMENT["rpm_rhel_version"],
            arch=config.DEPLOYMENT["rpm_arch"],
        )
        return re.compile(rf"{formatted_pattern_string}")

    def get_latest_upstream_rpm(self):
        """
        Fetch latest upstream RPM for Noobaa SA
        """
        # Fetch XML content from the URL
        s3_rpm_base_url = config.DEPLOYMENT["upstream_rpm_s3_base_url"]
        response = requests.get(s3_rpm_base_url)

        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_file_name = ""
            latest_file_date = datetime.min
            regex = self.get_rpm_pattern()
            query_base = "{http://s3.amazonaws.com/doc/2006-03-01/}"
            for content in root.findall(f"{query_base}Contents"):
                key = content.find(f"{query_base}Key").text
                last_modified = content.find(f"{query_base}LastModified").text
                if regex.match(key):
                    last_modified_date = datetime.strptime(
                        last_modified, "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                    if last_modified_date > latest_file_date:
                        latest_file_name = key
                        latest_file_date = last_modified_date
            if latest_file_name:
                log.info(f"Latest RPM: {latest_file_name}")
                return f"{s3_rpm_base_url}/{latest_file_name}"
            else:
                raise exceptions.rpmNotFoundError(
                    f"No RPM matching expression: {pattern}"
                )
        else:
            raise exceptions.rpmNotFoundError(
                f"Failed to fetch XML content from the URL: {s3_rpm_base_url}"
            )


class DeploymentNSFS(Deployment):
    """
    NooBaa Standalone deployment with NSFS
    """

    def __init__(self):
        """
        Initializes the necessary variables and install rpm needed for
        Noobaa SA Deployment with NSFS
        """
        super().__init__()
        self.install_rpm()
        self.noobaa_nsfs_service = "noobaa"
        node_rel_path = "node/bin/node"
        self.node_path = os.path.join(config.ENV_DATA["noobaa_core_dir"], node_rel_path)

    def install_noobaa_sa_nsfs(self):
        """
        Deploys NooBaa SA with NSFS
        """
        log.info("Installing Noobaa Standalone with NSFS")

        # create "noobaa.conf.d" directory
        noobaa_conf_dir = config.ENV_DATA["noobaa_conf_dir"]
        cmd = f"mkdir -p {noobaa_conf_dir}"
        exec_cmd(cmd=cmd, use_sudo=True)

        # create symbolic link
        source_path = config.ENV_DATA["nsfs_env"]
        target_path = os.path.join(noobaa_conf_dir, ".env")
        cmd = f"ln -s {source_path} {target_path}"
        exec_cmd(cmd=cmd, use_sudo=True)

        # start noobaa_nsfs service
        start_service(name=self.noobaa_nsfs_service, use_sudo=True)

        # checks noobaa_nsfs service
        is_nsfs_running = is_service_running(
            name=self.noobaa_nsfs_service, use_sudo=True
        )
        if not is_nsfs_running:
            raise ServiceRunningFailed("noobaa nsfs service is not running")

        # create symbolic link for node
        source_node_path = self.node_path
        target_node_path = os.path.join(
            config.ENV_DATA["bin_dir"], config.ENV_DATA["node_cmd"]
        )
        cmd = f"ln -s {source_node_path} {target_node_path}"
        exec_cmd(cmd=cmd, use_sudo=True)


class DeploymentDB(Deployment):
    """
    NooBaa Standalone deployment with DB
    """

    def __init__(self):
        """
        Initializes the necessary variables and install rpm needed for
        Noobaa SA Deployment with DB
        """
        super().__init__()
        self.postgres_repo = config.ENV_DATA["postgres_repo"]
        self.packages = config.ENV_DATA["db_packages"]
        self.postgresql_version = config.ENV_DATA["postgresql_version"]
        self.package = config.ENV_DATA["package_json"]
        self.npm = NPM(self.package)
        config.ENV_DATA["ip_address"] = get_ip_address()
        self.install_rpm()
        self.sleep = 10

    def install_noobaa_sa_db(self):
        """
        Installs Noobaa Standalone deployment with DB
        """
        log.info("Installing Noobaa Standalone with DB")

        # enable postgres repo
        install_rpm(rpm_path=self.postgres_repo)

        # enable postgresql version to default
        enable_postgresql_version(self.postgresql_version)

        # install postgresql
        install_rpm(packages=self.packages)

        # set permissions
        noobaa_core_dir = config.ENV_DATA["noobaa_core_dir"]
        set_permissions(directory_path=noobaa_core_dir, permissions=777, use_sudo=True)

        # create storage directory
        previous_dir = os.getcwd()
        storage_dir = config.ENV_DATA["storage_dir"]
        noobaa_core_dir = config.ENV_DATA["noobaa_core_dir"]
        os.chdir(noobaa_core_dir)
        create_directory(name=storage_dir)

        # set permissions to postgresql
        postgresql_dir = config.ENV_DATA["postgresql_dir"]
        set_permissions(directory_path=postgresql_dir, permissions=777, use_sudo=True)

        # initialize database directory
        self.initialize_db()

        # run database
        self.run_db()

        # creates DB
        self.create_db()

        # create .env file
        self.generate_env_file()

        # create config-local.js
        self.generate_config_local()

        # run web service
        self.run_web_service()

        # run bg service
        self.run_bg_service()

        # run hosted agents
        self.run_hosted_agents()

        # run s3 endpoint
        self.run_s3_service()

        # create backingstore drives
        backing_stores = config.DEPLOYMENT["backing_stores"]
        backing_store_drive_port = config.DEPLOYMENT["backing_store_drive_port"]
        for num in range(backing_stores):
            backing_store_path = config.DEPLOYMENT["backing_store_drive_path"]
            backing_store_drive = os.path.join(
                backing_store_path,
                f'{config.DEPLOYMENT["backing_store_drive_prefix"]}{num}',
            )
            create_directory(name=backing_store_drive)

            # run backingstore
            backing_store_drive_port += 1
            self.run_backingstore(
                backingstore_path=backing_store_drive, port=backing_store_drive_port
            )
            time.sleep(self.sleep)

        # check storage status
        self.check_storage_status()

        # check node status
        self.check_node_status()

        # switch to original directory
        os.chdir(previous_dir)

    def initialize_db(self):
        """
        Initialize DB
        """
        log.info("Initializing DB")
        self.npm.run_script(cmd="db:init")

    def run_db(self):
        """
        Runs the database
        """
        log.info("starting the DB")
        self.npm.run_script("db", wait=False)
        time.sleep(self.sleep)

    def create_db(self):
        """
        Creates DB
        """
        log.info("Creating DB, users and permissions")
        self.npm.run_script(cmd="db:create")
        time.sleep(self.sleep)

    def run_web_service(self):
        """
        Runs the web service
        """
        log.info("starting the web service")
        self.npm.run_script("web", wait=False)
        time.sleep(self.sleep)

    def run_bg_service(self):
        """
        Runs the bg service
        """
        log.info("starting the bg service")
        self.npm.run_script("bg", wait=False)
        time.sleep(self.sleep)

    def run_s3_service(self):
        """
        Runs the bg service
        """
        log.info("starting the s3 endpoint service")
        self.npm.run_script("s3", wait=False)
        time.sleep(self.sleep)

    def run_hosted_agents(self):
        """
        Runs hosted agent service
        """
        log.info("starting the hosted agent service")
        self.npm.run_script("hosted_agents", wait=False)
        time.sleep(self.sleep)

    def run_backingstore(self, backingstore_path, port):
        """
        Runs the backingstore

        Args:
            backingstore_path (str): path to backingstore drive
            port (int): Port number to start the backingstore drive

        """
        log.info(f"running backing store '{backingstore_path}' at port {port}")
        args = "--", f"{backingstore_path}", "--port", f"{port}"
        script_name = "backingstore"
        self.npm.run_script(cmd=script_name, args=args, wait=False)

    def check_storage_status(self):
        """
        Checks Storage status

        Raises:
            StorageCheckFailed: In case storage check failed

        """
        log.info("checking storage status")
        script_name = "api"
        args = "--", "node", "sync_monitor_to_store"
        op = self.npm.run_script(cmd=script_name, args=args)
        if op != 0:
            raise StorageStatusCheckFailed
        else:
            log.info("Storage Check successfully passed")

    def check_node_status(self):
        """
        Checks aggregate node status

        Raises:
            StorageCheckFailed: In case storage check failed

        """
        log.info("checking aggregate node status")
        script_name = "api"
        args = "--", "node", "aggregate_nodes", "{}"
        op = self.npm.run_script(cmd=script_name, args=args)
        if op != 0:
            raise AggregateNodeStatusCheckFailed
        else:
            log.info("Aggregate node status check successfully passed")

    def generate_env_file(self):
        """
        Creates .env file
        """
        log.info("creating .env file")
        templating = Templating(base_path=config.ENV_DATA["template_dir"])
        env_template = "env.j2"
        env_str = templating.render_template(env_template, config.ENV_DATA)
        env_file = config.ENV_DATA["env_file"]
        cmd = f"touch {env_file}"
        exec_cmd(cmd=cmd, use_sudo=True)
        cmd_permissions = f"chmod 666 {env_file}"
        exec_cmd(cmd=cmd_permissions, use_sudo=True)
        with open(env_file, "w") as f:
            f.write(env_str)

    def generate_config_local(self):
        """
        Creates config-local
        """
        log.info("creating config-local.js file")
        config_local = os.path.join(config.ENV_DATA["template_dir"], "config-local.js")
        cmd = f'cp {config_local} {config.ENV_DATA["config_local"]}'
        exec_cmd(cmd=cmd, use_sudo=True)


def deploy():
    """
    Deploys NooBaa as a Standalone
    """
    if config.ENV_DATA["db_installation"]:
        dep = DeploymentDB()
        dep.install_noobaa_sa_db()
    if config.ENV_DATA["nsfs_installation"]:
        dep = DeploymentNSFS()
        dep.install_noobaa_sa_nsfs()
