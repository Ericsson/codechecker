class AuthService {
  constructor() {
    this.ID_TOKEN_KEY = "__ccPrivilegedAccessToken";
  } 

  getToken() {
    return localStorage.getItem(this.ID_TOKEN_KEY);
  }

  saveToken(token) {
    localStorage.setItem(this.ID_TOKEN_KEY, token);
  }

  destroyToken() {
    localStorage.removeItem(this.ID_TOKEN_KEY);
  }
  
  getClient() {
    return { 
      hasPermission: permission => {
        const token = this.getToken();
        if (!token) return false;

        if (!permission) {
          return false;
        }

        return true;
      },
    };
  }
}

const authService = new AuthService();
export default authService;
