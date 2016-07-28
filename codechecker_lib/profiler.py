# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from datetime import datetime
import cProfile
import pstats
import StringIO

from codechecker_lib import logger

LOG = logger.get_new_logger('PROFILER')


def timeit(function):
    '''
    Decorator to measure function call time.
    '''

    func_name = function.__name__

    def debug_wrapper(*args, **kwargs):
        '''
        Log measured time.
        '''
        before = datetime.now()
        res = function(*args, **kwargs)
        after = datetime.now()
        timediff = after - before
        diff = timediff.microseconds/1000
        LOG.debug('['+str(diff)+'ms] ' + func_name)
        return res

    def release_wrapper(*args, **kwargs):
        '''
        No logging and measuring.
        '''
        res = function(*args, **kwargs)
        return res

    if logger.get_log_level() == logger.DEBUG:
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
