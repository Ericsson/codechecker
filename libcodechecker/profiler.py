# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from datetime import datetime
import cProfile
import pstats

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

from libcodechecker import logger
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('PROFILER')


class Timer(object):
    """
    Simple timer context manager
    to measure code block execution time.
    """
    def __init__(self, block_name=''):
        self.block_name = block_name

    def __enter__(self):
        self.before = datetime.datetime.now()

    def __exit__(self, type, value, traceback):
        after = datetime.datetime.now()
        time_diff = after - self.before
        LOG.debug(self.block_name + " " + str(time_diff.total_seconds())+'s')


def timeit(function):
    """
    Decorator to measure function call time.
    """

    func_name = function.__name__

    def debug_wrapper(*args, **kwargs):
        """
        Log measured time.
        """
        before = datetime.now()
        res = function(*args, **kwargs)
        after = datetime.now()
        timediff = after - before
        LOG.debug('['+str(timediff.total_seconds())+'s] ' + func_name)
        return res

    def release_wrapper(*args, **kwargs):
        """
        No logging and measuring.
        """
        res = function(*args, **kwargs)
        return res

    if LoggerFactory.get_log_level() == logger.DEBUG:
        return debug_wrapper
    else:
        return release_wrapper


def profileit(function):
    """
    Decorator to pofile function calls.
    """

    function_name = function.__name__

    def wrapper(*args, **kwargs):

        prof = cProfile.Profile()
        LOG.debug('Profiling: ' + function_name)
        prof.enable()
        res = function(*args, **kwargs)
        prof.disable()
        sortby = 'cumulative'

        prof_data = StringIO.StringIO()
        ps = pstats.Stats(prof, stream=prof_data).sort_stats(sortby)
        ps.print_stats()
        LOG.debug(prof_data.getvalue())
        prof_data.close()
        return res

    return wrapper
