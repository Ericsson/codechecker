# pylint: disable=invalid-name

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

# Server config
HOSTNAME = "0.0.0.0"
SERVERPORT = int(os.getenv("PORT")) if os.getenv("PORT") else 3000


class OauthServer(BaseHTTPRequestHandler):
    users_by_data = {
        "admin_github:admin": {
            "code": "0",
            "token": "github1"
        },
        "user_github:user": {
            "code": "1",
            "token": "github2"
        }
    }

    tokens_by_code = {
        "0": "github1",
        "1": "github2"
    }

    users_by_token = {
        "github1": {
            "login": "admin_github",
            "email": "admin@github.com",
            "name": "Admin @github",
        },
        "github2": {
            "login": "user_github",
            "email": "user@github.com",
            "name": "User @github",
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
                if query_result:
                    state = params['state']
                    code = query_result['code']
                    return self.show_json({"code": code, "state": state})
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

    def do_GET(self):
        if self.path.startswith("/login"):
            return self.login_tester()
        elif self.path.startswith("/get_user"):
            return self.get_user()
        return self.path

    def do_POST(self):
        params = {}
        raw = self.rfile.read(
            int(self.headers.get('Content-Length'))).decode("utf-8")
        for field in raw.split('&'):
            key, value = field.split('=')
            params[key] = value
        if "code" in params:
            code = params['code']
            if code in self.tokens_by_code:
                token = self.tokens_by_code[code]
                return self.show_json({
                    'access_token': token,
                    'token_type': "bearer",
                    'scope': "user:email",
                    'expires_in': 3600
                })
            else:
                return self.show_rejection("Invalid code")
        return self.path


webServer = HTTPServer((HOSTNAME, SERVERPORT), OauthServer)
webServer.allow_reuse_address = True
print(f"Server started http://{HOSTNAME}:{SERVERPORT}")

webServer.serve_forever()
webServer.server_close()
print("Server stopped.")
