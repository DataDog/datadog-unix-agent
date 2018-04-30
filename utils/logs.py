# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import sys
import logging
import logging.handlers
import traceback

from config import config

LOG_FORMAT = '%%(asctime)s | %%(levelname)s | dd.%s | %%(name)s(%%(filename)s:%%(lineno)s) | %%(message)s'
LOG_MAX_BYTES = 10 * 1024 * 1024


def get_log_date_format():
    return "%Y-%m-%d %H:%M:%S %Z"


def initialize_logging(logger_name):
    try:
        logging.basicConfig(
            format=LOG_FORMAT % logger_name,
            level=config.get('log_level', 'INFO').upper(),
        )

        log_settings = config.get('logging', {})

        log_file = log_settings.get('%s_log_file' % logger_name)
        if log_file is not None and not log_settings.get('disable_file_logging', False):
            # make sure the log directory is writeable
            # NOTE: the entire directory needs to be writable so that rotation works
            if os.access(os.path.dirname(log_file), os.R_OK | os.W_OK):
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=LOG_MAX_BYTES, backupCount=1)
                formatter = logging.Formatter(LOG_FORMAT % logger_name, get_log_date_format())
                file_handler.setFormatter(formatter)

                root_log = logging.getLogger()
                root_log.addHandler(file_handler)
            else:
                sys.stderr.write("Log file is unwritable: '%s'\n" % log_file)

    except Exception as e:
        sys.stderr.write("Couldn't initialize logging: %s\n" % str(e))
        traceback.print_exc()

        # if config fails entirely, enable basic stdout logging as a fallback
        logging.basicConfig(
            format=LOG_FORMAT % logger_name,
            level=logging.INFO,
        )

    # re-get the log after logging is initialized
    global log
    log = logging.getLogger(__name__)
