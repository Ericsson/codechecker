# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handles the management of stored user credentials and currently known session
tokens.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import os
import stat

import portalocker

from codechecker_common.logger import get_logger
from codechecker_common.util import check_file_owner_rw
from codechecker_common.util import load_json_or_empty

from codechecker_web.shared.version import SESSION_COOKIE_NAME as _SCN

LOG = get_logger('system')
SESSION_COOKIE_NAME = _SCN


class UserCredentials(object):

    def __init__(self):
        LOG.debug("Loading clientside session config.")

        # Check whether user's configuration exists.
        user_home = os.path.expanduser("~")
        session_cfg_file = os.path.join(user_home,
                                        ".codechecker.passwords.json")
        LOG.debug(session_cfg_file)

        scfg_dict = {}
        if os.path.exists(session_cfg_file):
            scfg_dict = load_json_or_empty(session_cfg_file, {},
                                           "user authentication")
        if os.path.exists(session_cfg_file):
            check_file_owner_rw(session_cfg_file)

        if not scfg_dict.get('credentials'):
            scfg_dict['credentials'] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict.get('client_autologin', True)

        # Check and load token storage for user.
        self.token_file = os.path.join(user_home, ".codechecker.session.json")
        LOG.debug(self.token_file)

        if os.path.exists(self.token_file):
            token_dict = load_json_or_empty(self.token_file, {},
                                            "user authentication")
            check_file_owner_rw(self.token_file)

            self.__tokens = token_dict.get('tokens')
        else:
            with open(self.token_file, 'w') as f:
                json.dump({'tokens': {}}, f)
            os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)

            self.__tokens = {}

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

        with open(self.token_file, 'w') as scfg:
            portalocker.lock(scfg, portalocker.LOCK_EX)
            json.dump({'tokens': self.__tokens}, scfg,
                      indent=2, sort_keys=True)
            portalocker.unlock(scfg)
