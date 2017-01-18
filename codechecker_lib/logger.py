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
import time

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


def add_verbose_arguments(parser):
    """
    Verbosity level arguments.
    """
    parser.add_argument('--verbose', type=str, dest='verbose',
                        choices=['info', 'debug', 'debug_analyzer'],
                        default='info',
                        help='Set verbosity level.')

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


class CustomFormatter(logging.Formatter):
    """
    Custom formatter to print log level in case of ERROR, WARNING
    or CRITICAL.
    """

    info_fmt = '[%(asctime)s] - %(message)s'
    error_fmt = '[%(levelname)s] [%(asctime)s] - %(message)s'
    debug_fmt = '[%(asctime)s] [%(process)d] <%(thread)d> - ' \
        '%(filename)s:%(lineno)d %(funcName)s() - %(message)s'

    def formatTime(self, record, datefmt=None):
        if LoggerFactory.log_level == logging.DEBUG or \
                LoggerFactory.log_level == logging.DEBUG_ANALYZER:
            return time.strftime('%H:%M:%S')
        else:
            return time.strftime('%H:%M')

    def format(self, record):

        # Save the original format
        format_orig = self._fmt

        # Replace the original format
        if record.levelno == logging.DEBUG:
            self._fmt = CustomFormatter.debug_fmt
        if record.levelno == logging.DEBUG_ANALYZER:
            self._fmt = CustomFormatter.debug_fmt
        elif record.levelno == logging.INFO:
            self._fmt = CustomFormatter.info_fmt
        elif record.levelno == logging.ERROR:
            self._fmt = CustomFormatter.error_fmt
        elif record.levelno == logging.WARNING:
            self._fmt = CustomFormatter.error_fmt
        elif record.levelno == logging.CRITICAL:
            self._fmt = CustomFormatter.error_fmt

        result = logging.Formatter.format(self, record)

        self._fmt = format_orig

        return result


class LoggerFactory(object):
    log_level = logging.INFO
    loggers = []

    short_format_handler = logging.StreamHandler(stream=sys.stdout)
    long_format_handler = logging.StreamHandler(stream=sys.stdout)

    short_format_handler.setFormatter(CustomFormatter())
    long_format_handler.setFormatter(CustomFormatter())

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

        if level == 'debug':
            cls.log_level = logging.DEBUG
        elif level == 'info':
            cls.log_level = logging.INFO
        elif level == 'debug_analyzer':
            cls.log_level = logging.DEBUG_ANALYZER
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
