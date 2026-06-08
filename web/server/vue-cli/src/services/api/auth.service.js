import ServiceClient from "@cc/auth";
import { BaseService } from "./_base.service";

const ID_TOKEN_KEY = "__ccPrivilegedAccessToken";

class AuthService extends BaseService {
  constructor() {
    super("Authentication", ServiceClient);
  }

  getToken() {
    return localStorage.getItem(ID_TOKEN_KEY);
  }

  saveToken(token) {
    localStorage.setItem(ID_TOKEN_KEY, token);
  }

  destroyToken() {
    localStorage.removeItem(ID_TOKEN_KEY);
  }
}

const authService = new AuthService();

export default authService;
