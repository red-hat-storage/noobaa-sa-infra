"""
This module loads the default logging conf to the logging system.
"""

import os
import time
import logging.config


current_directory = os.path.abspath(os.path.dirname(__file__))
logging_conf = os.path.join(current_directory, "logging.conf")

# Create a unique log filename with a timestamp
log_filename = time.strftime("%Y%m%d%H%M%S")
logging.config.fileConfig(fname=logging_conf, disable_existing_loggers=False)
