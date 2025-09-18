import { Permission } from "@cc/shared-types";

class AuthService {
  constructor() {
    this.ID_TOKEN_KEY = "__ccPrivilegedAccessToken";
    this._permList = [ Permission.SUPERUSER, Permission.PERMISSION_VIEW ];
    this._ownersByPerm = new Map();
    this._permList.forEach(p => {
      this._ownersByPerm.set(p, {
        users: new Set(["123"]),
        groups: new Set(["123"])
      });
    });
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
    const self = this;
    return { 
      hasPermission(permission) {
        const token = self.getToken();
        if (!token) return false;
        if (!permission) return false;
        return true;
      },

      getPermissionsForUser(scope, extraParamsJSON, filter, cb) {
        Promise.resolve().then(() => cb(self._permList));
      },

      getAuthorisedNames(permission, extraParamsJSON, cb) {
        const owners = self._ownersByPerm.get(permission);
        const res = {
          users: owners ? Array.from(owners.users) : [],
          groups: owners ? Array.from(owners.groups) : []
        };
        Promise.resolve().then(() => cb(res));
      },

      addPermission(permission, name, isGroup, extraParamsJSON, cb) {
        const owners = self._ownersByPerm.get(permission);
        if (!owners) { Promise.resolve().then(() => cb(false)); return; }
        if (isGroup) owners.groups.add(name); else owners.users.add(name);
        Promise.resolve().then(() => cb(true));
      },

      removePermission(permission, name, isGroup, extraParamsJSON, cb) {
        const owners = self._ownersByPerm.get(permission);
        if (!owners) { Promise.resolve().then(() => cb(false)); return; }
        if (isGroup) owners.groups.delete(name); else owners.users.delete(name);
        Promise.resolve().then(() => cb(true));
      }
    };
  }
}

const authService = new AuthService();

export { authService };
export default authService;
