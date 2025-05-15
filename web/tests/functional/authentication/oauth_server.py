# pylint: disable=invalid-name

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from authlib.oauth2.rfc7636 import create_s256_code_challenge as hash_s256

# Server config
HOSTNAME = "0.0.0.0"
SERVERPORT = int(os.getenv("PORT")) if os.getenv("PORT") else 3000


class OauthServer(BaseHTTPRequestHandler):
    users_by_data = {
        "admin_github:admin": {
            "code": "1",
            "token": "github1"
        },
        "user_github:user": {
            "code": "2",
            "token": "github2"
        },
        "user_google:user": {
            "code": "3",
            "token": "google3"
        },
        "user_dummy:user": {
            "code": "4",
            "token": "dummy4"
        },
        "user_csrf:user": {
            "code": "5",
            "token": "user_csrf5"
        },
        "user_pkce:user": {
            "code": "6",
            "token": "user_pkce6"
        },
        "user_incomplete_token:user": {
            "code": "7",
            "token": "user_incomplete_token7"
        }
    }

    tokens_by_code = {
        "1": "github1",
        "2": "github2",
        "3": "google3",
        "4": "dummy4",
        "5": "user_csrf5",
        "6": "user_pkce6",
        "7": "user_incomplete_token7"
    }

    # Store pkce code challenge
    code_challenges = {}

    users_by_token = {
        "github1": {
            "login": "admin_github",
            "email": "admin@github.com",
            "name": "Admin @github"
        },
        "github2": {
            "login": "user_github",
            "email": "user@github.com",
            "name": "User @github"
        },
        "google3": {
            "login": "user_google",
            "email": "user@google.com",
            "name": "User @google"
        },
        "dummy4": {
            "login": "user_dummy",
            "email": "dummy@dummy.com",
            "name": "User @dummy"
        },
        "user_csrf5": {
            "login": "user_csrf",
            "email": "user_csrf5@fake.com",
            "name": "User @csrf"
        },
        "user_pkce6": {
            "login": "user_pkce6",
            "email": "user_pkce6@fake.com",
            "name": "User @pkce"
        },
        "user_incomplete_token7": {
            "login": "user_incomplete_token",
            "email": "user_incomplete_token@fake.com",
            "name": "User @incomplete_token"
        }
    }

    def show_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(data), "utf-8"))
        return self.path

    def show_rejection(self, message):
        self.send_response(400)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps({"error": message}), "utf-8"))
        return self.path

    def login_tester(self):
        try:
            query_params = self.path.split('?')[1]
            params = {}
            for param in query_params.split('&'):
                key, value = param.split('=')
                params[key] = value

            if "username" in query_params:
                query = f"{params['username']}:{params['password']}"
                query_result = self.users_by_data.get(query, None)
                # csrf attack case
                if params['username'] == "user_csrf":
                    print("CSRF attack detected")
                    state = "fake_state"
                    code = query_result['code']
                    code_challenge = params['code_challenge']
                    # store code_challenge in the server
                    self.code_challenges[code] = {
                        "code_challenge": code_challenge,
                        "code_challenge_method": params[
                            'code_challenge_method']}

                    return self.show_json({"code": code,
                                           "state": state})
                # normal case
                elif query_result:
                    state = params['state']
                    code = query_result['code']
                    code_challenge = params['code_challenge']
                    # store code_challenge in the server
                    self.code_challenges[code] = {
                        "code_challenge": code_challenge,
                        "code_challenge_method": params[
                            'code_challenge_method']}

                    return self.show_json({"code": code,
                                           "state": state})
            return self.show_rejection("Invalid credentials")
        except IndexError:
            return self.show_rejection("Invalid query parameters")

    def get_user(self):
        token = self.headers.get("Authorization").split("Bearer ")[1]
        user = self.users_by_token.get(token, None)
        if user:
            return self.show_json(user)
        else:
            return self.show_rejection("Invalid token")

    def handle_user_token_request(self):
        params = {}
        raw = self.rfile.read(
            int(self.headers.get('Content-Length'))).decode("utf-8")
        for field in raw.split('&'):
            key, value = field.split('=')
            params[key] = value
            print(f"key: {key}, value: {value}")
        if "code" in params:
            code = params['code']
            # check for PKCE code challenge similarity
            if code in self.code_challenges:

                entry = self.code_challenges[code]
                code_challenge = entry.get("code_challenge", None)
                code_challenge_method = entry.get(
                    "code_challenge_method", None)

                if code_challenge_method and \
                        code_challenge_method == "S256":
                    # PKCE verifier
                    if code_challenge:
                        if hash_s256(params['code_verifier']) != \
                                code_challenge:
                            return self.show_rejection("Invalid code verifier")
                else:
                    return self.show_rejection("Invalid code challenge method")
            # return incomplete token information for test purposes.
            if code == "7":
                return self.show_json({
                    'access_token': "user_incomplete_token7",
                })
            if code in self.tokens_by_code:
                token = self.tokens_by_code[code]
                return self.show_json({
                    'access_token': token,
                    'refresh_token': token,
                    'token_type': "bearer",
                    'scope': "user:email",
                    'expires_in': 3600
                })
            else:
                return self.show_rejection("Invalid code")
        return self.path

    def do_GET(self):
        if self.path.startswith("/login"):
            return self.login_tester()
        elif self.path.startswith("/get_user"):
            return self.get_user()
        return self.path

    def do_POST(self):
        if self.path.endswith("/token"):
            return self.handle_user_token_request()
        else:
            return self.show_rejection("Unsupported POST path")


webServer = HTTPServer((HOSTNAME, SERVERPORT), OauthServer)
webServer.allow_reuse_address = True
print(f"Server started http://{HOSTNAME}:{SERVERPORT}")

webServer.serve_forever()
webServer.server_close()
print("Server stopped.")
