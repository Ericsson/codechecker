const ID_TOKEN_KEY = "__ccPrivilegedAccessToken";

class TokenService {
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

const tokenService = new TokenService();

export default tokenService;