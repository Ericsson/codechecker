# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Tests for extending expired OAuth sessions. """

import json
import os
import shutil
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from codechecker_server.database.config_db_model import \
    Base, OAuthToken, Session as SessionRecord
from codechecker_server.session_manager import SessionManager


class _TokenHandler(BaseHTTPRequestHandler):
    """ Mock OAuth token endpoint. """

    def log_message(self, *args):
        pass

    def do_POST(self):  # pylint: disable=invalid-name
        length = int(self.headers.get('Content-Length', 0))
        self.server.requests.append(self.rfile.read(length).decode())

        if self.server.mode == 'ok':
            code, body = 200, json.dumps({
                'access_token': 'new_access',
                'refresh_token': 'new_refresh',
                'token_type': 'bearer',
                'scope': 'openid email profile',
                'expires_in': 3600}).encode()
            content_type = 'application/json'
        elif self.server.mode == 'reject':
            code, body = 400, json.dumps({
                'error': 'invalid_grant'}).encode()
            content_type = 'application/json'
        else:
            code, body = 500, b'Internal Server Error'
            content_type = 'text/plain'

        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(body)


class OAuthSessionExtensionTest(unittest.TestCase):
    """ Tests for SessionManager OAuth session extension. """

    def setUp(self):
        self.oauth_server = HTTPServer(('localhost', 0), _TokenHandler)
        self.oauth_server.mode = 'ok'
        self.oauth_server.requests = []
        threading.Thread(target=self.oauth_server.serve_forever,
                         daemon=True).start()
        oauth_host = f"http://localhost:{self.oauth_server.server_port}"

        self.workspace = tempfile.mkdtemp()

        default_cfg = os.path.join(os.environ['REPO_ROOT'], 'web', 'server',
                                   'config', 'server_config.json')
        with open(default_cfg, encoding='utf-8') as f:
            cfg = json.load(f)

        auth = cfg['authentication']
        auth['enabled'] = True
        auth['session_lifetime'] = 300
        auth['refresh_time'] = 60
        auth['method_oauth'] = {
            'enabled': True,
            'shared_variables': {
                'host': 'http://localhost:8080',
                'oauth_host': oauth_host
            },
            'providers': {
                'github': {
                    'enabled': True,
                    'client_id': '1',
                    'client_secret': '1',
                    'template': 'github/v1',
                    'authorization_url': '{oauth_host}/login',
                    'token_url': '{oauth_host}/token',
                    'user_info_url': '{oauth_host}/get_user',
                    'scope': 'openid email profile',
                    'user_info_mapping': {'username': 'login'}
                }
            }
        }

        cfg_file = os.path.join(self.workspace, 'server_config.json')
        with open(cfg_file, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        os.chmod(cfg_file, 0o600)

        self.engine = create_engine(
            'sqlite:///' + os.path.join(self.workspace, 'config.sqlite'))
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)

        self.manager = SessionManager(
            self.db, cfg_file, os.path.join(self.workspace, 'secrets.json'))

        self.old_access = datetime.now() - timedelta(hours=1)

    def tearDown(self):
        self.oauth_server.shutdown()
        self.oauth_server.server_close()
        self.engine.dispose()
        shutil.rmtree(self.workspace)

    def __insert_session(self, access_token_expires_at):
        """ Inserts an expired session and returns its token. """
        token = uuid.uuid4().hex
        with self.db() as transaction:
            record = SessionRecord(token, 'admin_github', '')
            record.last_access = self.old_access
            transaction.add(record)
            transaction.flush()

            transaction.add(OAuthToken('github', 'old_access',
                                       access_token_expires_at,
                                       'old_refresh', record.id))
            transaction.commit()
        return token

    def __get_db_state(self, token):
        with self.db() as transaction:
            record, oauth_token = transaction \
                .query(SessionRecord, OAuthToken) \
                .join(OAuthToken,
                      OAuthToken.auth_session_id == SessionRecord.id) \
                .filter(SessionRecord.token == token) \
                .one()
            return record.last_access, oauth_token

    def __assert_recent(self, timestamp):
        self.assertLess(abs((datetime.now() - timestamp).total_seconds()), 5)

    def test_valid_access_token_extends_locally(self):
        """ Valid access token, no refresh needed. """
        token = self.__insert_session(datetime.now() + timedelta(hours=1))

        session = self.manager.get_session(token)

        self.assertIsNotNone(session)
        self.assertEqual(self.oauth_server.requests, [])

        last_access, oauth_token = self.__get_db_state(token)
        self.__assert_recent(last_access)
        self.__assert_recent(session.last_access)
        self.assertEqual(oauth_token.access_token, 'old_access')

    def test_expired_access_token_is_refreshed(self):
        """ Expired access token is refreshed and stored. """
        token = self.__insert_session(datetime.now() - timedelta(minutes=1))

        session = self.manager.get_session(token)

        self.assertIsNotNone(session)
        self.assertEqual(len(self.oauth_server.requests), 1)
        self.assertIn('grant_type=refresh_token',
                      self.oauth_server.requests[0])
        self.assertIn('refresh_token=old_refresh',
                      self.oauth_server.requests[0])

        last_access, oauth_token = self.__get_db_state(token)
        self.__assert_recent(last_access)
        self.__assert_recent(session.last_access)
        self.assertEqual(oauth_token.access_token, 'new_access')
        self.assertEqual(oauth_token.refresh_token, 'new_refresh')
        self.assertAlmostEqual(
            (oauth_token.expires_at - datetime.now()).total_seconds(),
            3600, delta=10)

    def test_cached_session_is_refreshed(self):
        """ Same for a session cached in memory. """
        token = self.__insert_session(datetime.now() + timedelta(hours=1))
        session = self.manager.get_session(token)

        session.last_access = self.old_access
        with self.db() as transaction:
            transaction.query(OAuthToken) \
                .filter(OAuthToken.access_token == 'old_access') \
                .update({'expires_at': datetime.now() - timedelta(minutes=1)})
            transaction.commit()

        self.assertIs(self.manager.get_session(token), session)
        self.assertEqual(len(self.oauth_server.requests), 1)
        self.__assert_recent(session.last_access)

        _, oauth_token = self.__get_db_state(token)
        self.assertEqual(oauth_token.access_token, 'new_access')

    def test_rejected_refresh_token(self):
        """ Rejected refresh token ends the session, logged as info. """
        self.oauth_server.mode = 'reject'
        token = self.__insert_session(datetime.now() - timedelta(minutes=1))

        with self.assertLogs('server', level='INFO') as logs:
            self.assertIsNone(self.manager.get_session(token))

        self.assertTrue(any('invalid_grant' in line and
                            line.startswith('INFO')
                            for line in logs.output))
        self.assertFalse(any(line.startswith(('WARNING', 'ERROR'))
                             for line in logs.output))

    def test_provider_error(self):
        """ Provider error ends the session, logged as error. """
        self.oauth_server.mode = 'error'
        token = self.__insert_session(datetime.now() - timedelta(minutes=1))

        with self.assertLogs('server', level='ERROR') as logs:
            self.assertIsNone(self.manager.get_session(token))

        self.assertTrue(any('OAuth session extension failed' in line
                            for line in logs.output))


if __name__ == '__main__':
    unittest.main()
