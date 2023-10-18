"""
Main module
"""

from deployment.deployment import deploy
from framework.customizations.arg_parser import load_args
from framework.customizations.logging import logging

log = logging.getLogger(__name__)


def noobaa_sa_install():
    """
    Installs NooBaa Standalone
    """
    log.info("Installing Noobaa Standalone")
    load_args()
    deploy()
