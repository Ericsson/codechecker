# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from codechecker import util
from codechecker import globalConfig
from codechecker import logger


def get_env_checkers_list(env_name):
    env_set_checkers = util.get_env_var(env_name)

    log = logger.get_new_logger("CHECKERS")
    log.debug('Getting checkers list from environment variable %s' % (env_name))

    if env_set_checkers:
        checkers_list = env_set_checkers.split(':')
        log.debug('Checkers list is -> ' + env_set_checkers)
        return sorted(checkers_list)
    else:
        log.debug('No checkers list was defined.')
        return None


def get_enabled_checkers():
    config = globalConfig.GlobalConfig()
    env_checkers = get_env_checkers_list(config.envEnableCheckersName)

    return env_checkers


def get_disabled_checkers():
    config = globalConfig.GlobalConfig()
    env_checkers = get_env_checkers_list(config.envDisableCheckersName)

    return env_checkers
