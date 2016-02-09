# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
'''

import os
import sys
import logging

# the logging leves can be accesses without
# importing the logging module in other modules
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
def get_log_level():
    '''
    '''
    level = os.getenv('CODECHECKER_VERBOSE')
    if level:
        if level == 'debug':
            return logging.DEBUG

    return logging.INFO


# ------------------------------------------------------------------------------
def get_new_logger(logger_name, out_stream=sys.stdout):
    '''
    '''

    loglevel = get_log_level()
    logger = logging.getLogger('[' + logger_name + ']')
    stdout_handler = logging.StreamHandler(stream=out_stream)

    #
    if not getattr(logger, 'handlers'):
        if loglevel == logging.DEBUG:
                # FIXME create a new handler to write all log messages into a file
                # FIXME filter stdout messages only from analyzer, parser,
                # report, sourceDep (any other?) are printed out to the stdout
            logger.setLevel(logging.DEBUG)
            stdout_handler.setLevel(logging.DEBUG)
            format_str = '[%(process)d] <%(thread)d> - %(filename)s:%(lineno)d %(funcName)s() - %(message)s'
            msg_formatter = logging.Formatter(format_str)
            stdout_handler.setFormatter(msg_formatter)
            logger.addHandler(stdout_handler)
        else:
            logger.setLevel(logging.INFO)
            stdout_handler.setLevel(logging.INFO)
            msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
            stdout_handler.setFormatter(msg_formatter)
            logger.addHandler(stdout_handler)

    return logger
