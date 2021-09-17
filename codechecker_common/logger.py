# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""


import argparse
import json
import logging
from logging import config
import os


# The logging leaves can be accesses without
# importing the logging module in other modules.
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
NOTSET = logging.NOTSET

CMDLINE_LOG_LEVELS = ['info', 'debug_analyzer', 'debug']

DEBUG_ANALYZER = logging.DEBUG_ANALYZER = 15  # type: ignore
logging.addLevelName(DEBUG_ANALYZER, 'DEBUG_ANALYZER')


class CCLogger(logging.Logger):
    def __init__(self, name, level=NOTSET):
        super(CCLogger, self).__init__(name, level)

    def debug_analyzer(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG_ANALYZER):
            self._log(logging.DEBUG_ANALYZER, msg, args, **kwargs)


logging.setLoggerClass(CCLogger)

data_files_dir_path = os.environ.get('CC_DATA_FILES_DIR', '')
DEFAULT_LOG_CFG_FILE = os.path.join(data_files_dir_path, 'config',
                                    'logger.conf')


# Default config which can be used if reading log config from a
# file fails.
DEFAULT_LOG_CONFIG = '''{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "brief": {
      "format": "[%(asctime)s][%(levelname)s] - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M"
    },
    "precise": {
      "format": "[%(levelname)s] [%(asctime)s] {%(name)s} [%(process)d] \
<%(thread)d> - %(filename)s:%(lineno)d %(funcName)s() - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M"
    }
  },
  "handlers": {
    "default": {
      "level": "INFO",
      "formatter": "brief",
      "class": "logging.StreamHandler"
    }
  },
  "loggers": {
    "": {
      "handlers": ["default"],
      "level": "INFO",
      "propagate": true
    }
  }
}'''


try:
    with open(DEFAULT_LOG_CFG_FILE, 'r',
              encoding="utf-8", errors="ignore") as dlc:
        DEFAULT_LOG_CONFIG = dlc.read()
except IOError as ex:
    print(ex)
    print("Failed to load logger configuration. Using built-in config.")


def add_verbose_arguments(parser):
    """
    Verbosity level arguments.
    """
    parser.add_argument('--verbose', type=str, dest='verbose',
                        choices=CMDLINE_LOG_LEVELS,
                        default=argparse.SUPPRESS,
                        help='Set verbosity level.')


def get_logger(name):
    """
    Return a logger instance if already exists with the given name.
    """
    return logging.getLogger(name)


def validate_loglvl(log_level):
    """
    Should return a valid log level name
    """
    log_level = log_level.upper()

    if log_level not in {lev.upper() for lev in CMDLINE_LOG_LEVELS}:
        return "INFO"

    return log_level


class LOG_CFG_SERVER:
    """
    Initialize a log configuration server for dynamic log configuration.
    The log config server will only be started if the
    'CC_LOG_CONFIG_PORT' environment variable is set.
    """

    def __init__(self, log_level='INFO'):

        # Configure the logging with the default config.
        setup_logger(log_level)

        self.log_server = None

        log_cfg_port = os.environ.get('CC_LOG_CONFIG_PORT')

        if log_cfg_port:
            self.log_server = config.listen(int(log_cfg_port))
            self.log_server.start()

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        if self.log_server:
            config.stopListening()
            self.log_server.join()


def setup_logger(log_level=None, stream=None):
    """
    Modifies the log configuration.
    Overwrites the log levels for the loggers and handlers in the
    configuration.
    Redirects the output of all handlers to the given stream. Short names can
    be given (stderr -> ext://sys.stderr, 'stdout' -> ext://sys.stdout).
    """

    LOG_CONFIG = json.loads(DEFAULT_LOG_CONFIG)
    if log_level:
        log_level = validate_loglvl(log_level)

        loggers = LOG_CONFIG.get("loggers", {})
        for k in loggers.keys():
            LOG_CONFIG['loggers'][k]['level'] = log_level

        handlers = LOG_CONFIG.get("handlers", {})
        for k in handlers.keys():
            LOG_CONFIG['handlers'][k]['level'] = log_level
            if log_level == 'DEBUG' or log_level == 'DEBUG_ANALYZER':
                LOG_CONFIG['handlers'][k]['formatter'] = 'precise'

    if stream:
        if stream == 'stderr':
            stream = 'ext://sys.stderr'
        elif stream == 'stdout':
            stream = 'ext://sys.stdout'

        handlers = LOG_CONFIG.get("handlers", {})
        for k in handlers.keys():
            handler = LOG_CONFIG['handlers'][k]
            if 'stream' in handler:
                handler['stream'] = stream

    config.dictConfig(LOG_CONFIG)
