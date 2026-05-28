import { Client as ServiceClient } from "@cc/auth";
import { BaseService } from "./_base.service";
import tokenService from "./token.service";

class AuthService extends BaseService {
  constructor() {
    super("Authentication", ServiceClient);
  }

  getToken() {
    return tokenService.getToken();
  }

  saveToken(token) {
    tokenService.saveToken(token);
  }

  destroyToken() {
    tokenService.destroyToken();
  }
}

const authService = new AuthService();

export default authService;
