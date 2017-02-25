# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from codechecker import globalConfig
from codechecker import util
from codechecker.logger import LoggerFactory


def get_env_checkers_list(env_name):
    env_set_checkers = util.get_env_var(env_name)

    LOG = LoggerFactory.get_new_logger("CHECKERS")
    LOG.debug_analyzer('Getting checkers list from environment variable %s'
                       % env_name)

    if env_set_checkers:
        checkers_list = env_set_checkers.split(':')
        LOG.debug_analyzer('Checkers list is -> ' + env_set_checkers)
        return sorted(checkers_list)
    else:
        LOG.debug_analyzer('No checkers list was defined.')
        return None


def get_enabled_checkers():
    config = globalConfig.GlobalConfig()
    env_checkers = get_env_checkers_list(config.envEnableCheckersName)

    return env_checkers


def get_disabled_checkers():
    config = globalConfig.GlobalConfig()
    env_checkers = get_env_checkers_list(config.envDisableCheckersName)

    return env_checkers
