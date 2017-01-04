# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

import logging
import os
import sys

# The logging leaves can be accesses without
# importing the logging module in other modules.
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
NOTSET = logging.NOTSET


class BColors(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


# ------------------------------------------------------------------------------
logging.DEBUG_ANALYZER = 15
logging.addLevelName(logging.DEBUG_ANALYZER, 'DEBUG_ANALYZER')


class CCLogger(logging.Logger):
    def __init__(self, name, level=NOTSET):
        super(CCLogger, self).__init__(name, level)

    def debug_analyzer(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG_ANALYZER):
            self._log(logging.DEBUG_ANALYZER, msg, args, **kwargs)


logging.setLoggerClass(CCLogger)


class LoggerFactory(object):
    log_level = logging.INFO
    loggers = []

    short_format_handler = logging.StreamHandler(stream=sys.stdout)
    long_format_handler = logging.StreamHandler(stream=sys.stdout)

    short_format_handler.setFormatter(logging.Formatter(
        '[%(levelname)s] - %(message)s'))
    long_format_handler.setFormatter(logging.Formatter(
        '[%(process)d] <%(thread)d> - '
        '%(filename)s:%(lineno)d %(funcName)s() - %(message)s'))

    handlers = {
        logging.INFO: short_format_handler,
        logging.DEBUG: long_format_handler,
        logging.DEBUG_ANALYZER: short_format_handler}

    @classmethod
    def get_log_level(cls):
        return cls.log_level

    @classmethod
    def set_log_level(cls, level):

        for logger in cls.loggers:
            logger.removeHandler(cls.handlers[LoggerFactory.log_level])

        if level == 1:
            cls.log_level = logging.DEBUG_ANALYZER
        elif level > 1:
            cls.log_level = logging.DEBUG
        else:
            cls.log_level = logging.INFO

        cls.short_format_handler.setLevel(cls.log_level)
        cls.long_format_handler.setLevel(cls.log_level)

        for logger in cls.loggers:
            logger.setLevel(cls.log_level)
            logger.addHandler(cls.handlers[cls.log_level])

    @classmethod
    def get_new_logger(cls, logger_name):
        logger = logging.getLogger('[' + logger_name + ']')

        logger.setLevel(cls.log_level)
        logger.addHandler(cls.handlers[cls.log_level])

        cls.loggers.append(logger)

        return logger
