# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

import logging
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


DEBUG_ANALYZER = logging.DEBUG_ANALYZER = 15
logging.addLevelName(DEBUG_ANALYZER, 'DEBUG_ANALYZER')


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

    # Short format strings where only the time and the message is printed.
    format_string_short = {
        'info_fmt':  '[%(asctime)s] - %(message)s',
        'error_fmt': '[%(levelname)s] [%(asctime)s] - %(message)s',
        'debug_fmt': '[%(asctime)s] {%(name)s} [%(process)d] <%(thread)d> - '
                     '%(filename)s:%(lineno)d %(funcName)s() - %(message)s'
    }

    # In a more verbose mode (such as --verbose debug), the error messages
    # should also be a bit more verbose.
    format_strings_verbose = {
        'info_fmt': '[%(asctime)s] {%(name)s} - '
                    '%(filename)s:%(lineno)d %(funcName)s() - %(message)s',
        'error_fmt': '[%(levelname)s] [%(asctime)s] {%(name)s} - '
                     '%(filename)s:%(lineno)d %(funcName)s() - %(message)s',
        'debug_fmt': '[%(asctime)s] {%(name)s} [%(process)d] <%(thread)d> - '
                     '%(filename)s:%(lineno)d %(funcName)s() - %(message)s'
    }

    # This sets to which --verbose (loglevel), what verbosity strings should
    # be used by the loggers.
    formatter_map = {
        logging.DEBUG: format_strings_verbose,
        logging.DEBUG_ANALYZER: format_strings_verbose,
        logging.INFO: format_string_short,
        logging.ERROR: format_string_short,
        logging.WARNING: format_string_short,
        logging.CRITICAL: format_string_short
    }

    def __init__(self):
        self.level = logging.INFO
        super(CustomFormatter, self).__init__()

    def set_level(self, new_level):
        self.level = new_level

    def formatTime(self, record, datefmt=None):
        if LoggerFactory.log_level == logging.DEBUG or \
                LoggerFactory.log_level == logging.DEBUG_ANALYZER:
            return time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return time.strftime('%Y-%m-%d %H:%M')

    def format(self, record):

        # Save the original format
        format_orig = self._fmt

        # Get a format based on the most verbose loglevel set by the user.
        format_strings = CustomFormatter.formatter_map[self.level]

        # Replace the original format.
        if record.levelno == logging.DEBUG:
            self._fmt = format_strings['debug_fmt']
        if record.levelno == logging.DEBUG_ANALYZER:
            self._fmt = format_strings['debug_fmt']
        elif record.levelno == logging.INFO:
            self._fmt = format_strings['info_fmt']
        elif record.levelno == logging.ERROR:
            self._fmt = format_strings['error_fmt']
        elif record.levelno == logging.WARNING:
            self._fmt = format_strings['error_fmt']
        elif record.levelno == logging.CRITICAL:
            self._fmt = format_strings['error_fmt']

        result = logging.Formatter.format(self, record)

        self._fmt = format_orig

        return result


class LoggerFactory(object):
    log_level = logging.INFO
    loggers = []

    short_format_handler = logging.StreamHandler(stream=sys.stdout)
    long_format_handler = logging.StreamHandler(stream=sys.stdout)

    custom_formatter = CustomFormatter()

    short_format_handler.setFormatter(custom_formatter)
    long_format_handler.setFormatter(custom_formatter)

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
        elif level == 'debug_analyzer':
            cls.log_level = logging.DEBUG_ANALYZER
        elif level == 'info':
            cls.log_level = logging.INFO
        else:
            cls.log_level = logging.INFO

        cls.custom_formatter.set_level(cls.log_level)

        cls.short_format_handler.setLevel(cls.log_level)
        cls.long_format_handler.setLevel(cls.log_level)

        for logger in cls.loggers:
            logger.setLevel(cls.log_level)
            logger.addHandler(cls.handlers[cls.log_level])

    @classmethod
    def get_new_logger(cls, logger_name):
        logger = logging.getLogger(logger_name)

        logger.setLevel(cls.log_level)
        logger.addHandler(cls.handlers[cls.log_level])

        cls.loggers.append(logger)

        return logger
