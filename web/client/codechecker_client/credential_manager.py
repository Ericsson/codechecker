# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handles the management of stored user credentials and currently known session
tokens.
"""

import json
import os
import re
import stat

import portalocker

from codechecker_report_converter.util import load_json_or_empty

from codechecker_common.logger import get_logger

from codechecker_web.shared.env import check_file_owner_rw, get_password_file,\
    get_session_file
from codechecker_web.shared.version import SESSION_COOKIE_NAME as _SCN

LOG = get_logger('system')
SESSION_COOKIE_NAME = _SCN


def simplify_credentials(credentials):
    """ Replace the key of the entries with host:port values.

    Returns a new dictionary from the credentials where the key will be
    replaced by 'host:port' values so protocols and product names will be
    removed if these are given.
    """
    host_entry_pattern = re.compile(
        r'^(?P<protocol>http[s]?://)*(?P<host>[^:\/\s]+):*(?P<port>\d+)*'
        r'/*(?P<product>\w+)*$')

    ret = {}
    for host_entry, auth_string in credentials.items():
        match = host_entry_pattern.match(host_entry)
        if not match:
            LOG.warning("Not a valid host entry: %s.", host_entry)
            continue

        host = match.group('host')
        port = match.group('port')
        host_port = '{0}:{1}'.format(host, port) if port else host

        ret[host_port] = auth_string

    return ret


class UserCredentials:

    def __init__(self):
        LOG.debug("Loading clientside session config.")

        # Check whether user's configuration exists.
        session_cfg_file = get_password_file()
        LOG.info("Checking local passwords or tokens in %s", session_cfg_file)

        scfg_dict = {}

        user_home = os.path.expanduser("~")
        mistyped_cfg_file = os.path.join(user_home,
                                         ".codechecker.password.json")

        if os.path.exists(session_cfg_file):
            check_file_owner_rw(session_cfg_file)
            scfg_dict = load_json_or_empty(session_cfg_file, {},
                                           "user authentication")
            scfg_dict['credentials'] = \
                simplify_credentials(scfg_dict['credentials'])
            if not scfg_dict['credentials']:
                LOG.info("No saved tokens.")
            else:
                LOG.debug("Tokens or passwords were found for these hosts:")
                for k, v in scfg_dict['credentials'].items():
                    user, _ = v.split(":")
                    LOG.debug("  user '%s' host '%s'", user, k)
        elif os.path.exists(mistyped_cfg_file):
            LOG.warning("Typo in file name! Rename '%s' to '%s'.",
                        mistyped_cfg_file, session_cfg_file)
        else:
            LOG.info("Password file not found.")

        if not scfg_dict.get('credentials'):
            scfg_dict['credentials'] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict.get('client_autologin', True)
        # Check and load token storage for user.
        self.token_file = get_session_file()
        LOG.info("Checking for local valid sessions.")

        with open(self.token_file, 'a+',
                  encoding="utf-8", errors="ignore") as f:
            f.seek(0)

            try:
                portalocker.lock(f, portalocker.LOCK_EX)

                token_dict = json.loads(f.read())

                check_file_owner_rw(self.token_file)

                self.__tokens = token_dict.get('tokens', {})
                LOG.debug("Found session information for these hosts:")
                for k, _ in self.__tokens.items():
                    LOG.debug("  %s", k)
            except json.JSONDecodeError:
                json.dump({'tokens': {}}, f)
                os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)

                self.__tokens = {}
            finally:
                portalocker.unlock(f)

    def is_autologin_enabled(self):
        return self.__autologin

    def get_token(self, host, port):
        return self.__tokens.get("{0}:{1}".format(host, port))

    def get_auth_string(self, host, port):
        ret = self.__save['credentials'].get('{0}:{1}'.format(host, port))
        if not ret:
            ret = self.__save['credentials'].get(host)
        if not ret:
            ret = self.__save['credentials'].get('*:{0}'.format(port))
        if not ret:
            ret = self.__save['credentials'].get('*')

        return ret

    def save_token(self, host, port, token, destroy=False):
        if destroy:
            self.__tokens.pop('{0}:{1}'.format(host, port), None)
        else:
            self.__tokens['{0}:{1}'.format(host, port)] = token

        with open(self.token_file, 'w',
                  encoding="utf-8", errors="ignore") as scfg:
            portalocker.lock(scfg, portalocker.LOCK_EX)
            json.dump({'tokens': self.__tokens}, scfg,
                      indent=2, sort_keys=True)
            portalocker.unlock(scfg)
