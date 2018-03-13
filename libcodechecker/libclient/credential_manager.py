# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
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

from libcodechecker.logger import get_logger
from libcodechecker.util import check_file_owner_rw
from libcodechecker.util import load_json_or_empty
from libcodechecker.version import SESSION_COOKIE_NAME as _SCN

LOG = get_logger('system')
SESSION_COOKIE_NAME = _SCN


class UserCredentials(object):

    def __init__(self, password_file_content=None, tokens=None):
        LOG.debug("Loading clientside session config.")
        user_home = os.path.expanduser("~")

        scfg_dict = password_file_content

        if password_file_content is None:
            # Check whether user's configuration exists.
            session_cfg_file = os.path.join(user_home,
                                            ".codechecker.passwords.json")
            LOG.debug(session_cfg_file)

            if os.path.exists(session_cfg_file):
                scfg_dict = load_json_or_empty(session_cfg_file, {},
                                               "user authentication")
            if os.path.exists(session_cfg_file):
                check_file_owner_rw(session_cfg_file)

        if not scfg_dict.get('credentials'):
            scfg_dict['credentials'] = {}

        self.__save = scfg_dict
        self.__autologin = scfg_dict.get('client_autologin', True)

        self.__tokens = tokens
        if tokens is None:
            # Check and load token storage for user.
            self.token_file = os.path.join(user_home,
                                           ".codechecker.session.json")
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

    def is_autologin_enabled(self):
        return self.__autologin

    def get_token(self, host, port):
        return self.__tokens.get("{0}:{1}".format(host, port))

    def get_auth_string(self, host, port):
        """
        hostname without protocol and product url
        """
        p = re.compile(
            r'^(?P<protocol>http[s]?://)*(?P<host>[\w.\*]+):*(?P<port>\d+)*'
            r'/*(?P<product>\w+)*$')

        full_match = None
        host_only_match = None
        all_host_port = None
        all_host_no_port = None

        for host_entry, auth_string in self.__save['credentials'].items():
            match = p.match(host_entry)
            if match:
                host_match = match.group('host')
                port_match = match.group('port')
                if host_match == host and port == port_match:
                    full_match = auth_string
                if host_match == host:
                    host_only_match = auth_string
                if host_match == '*' and port_match == port:
                    all_host_port = auth_string
                if host_match == '*' and port_match is None:
                    all_host_no_port = auth_string

        if full_match:
            return full_match
        elif host_only_match:
            return host_only_match
        elif all_host_port:
            return all_host_port
        elif all_host_no_port:
            return all_host_no_port
        else:
            return None

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
