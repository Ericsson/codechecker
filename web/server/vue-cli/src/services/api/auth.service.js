import Cookies from "js-cookie";
import ServiceClient from "@cc/auth";
import { BaseService } from "./_base.service";

const ID_TOKEN_KEY = "__ccPrivilegedAccessToken";

class AuthService extends BaseService {
  constructor() {
    super("Authentication", ServiceClient);
  }

  getToken() {
    return Cookies.get(ID_TOKEN_KEY);
  }

  saveToken(token) {
    Cookies.set(ID_TOKEN_KEY, token);
  }

  destroyToken() {
    Cookies.remove(ID_TOKEN_KEY);
  }
}

const authService = new AuthService();

export default authService;
