import { authService, handleThriftError } from "@cc-api";
import { PermissionFilter } from "@cc/auth-types";
import { Permission } from "@cc/shared-types";

export default {
  name: "PopulatePermissionsMixin",
  data() {
    return {
      permissions: [],
      userAuthRights: {},
      groupAuthRights: {}
    };
  },
  methods: {
    pick(obj, names) {
      for (const n of names) {
        if (obj && typeof obj[n] === "function") {
          return obj[n].bind(obj);
        }
      }
      return undefined;
    },
    populatePermissions(scope, extraParamsJSON) {
      const filter = new PermissionFilter({ canManage: true });
      const listFn = this.pick(authService.getClient(), [
        "getPermissionsForUser",
        "listPermissionsForUser",
        "listPermissions",
        "getPermissions"
      ]);
      if (listFn) {
        listFn(scope, extraParamsJSON, filter, handleThriftError(permissions => {
          this.permissions = permissions;
          this.populateAuthRights(extraParamsJSON);
        }));
      } else {
        this.permissions = [
          Permission.SUPERUSER,
          Permission.PERMISSION_VIEW
        ].filter(v => v !== undefined);
        this.populateAuthRights(extraParamsJSON);
      }
    },

    addAuthRight(authRights, permission, userNames) {
      userNames.forEach(userName => {
        if (!(userName in authRights)) {
          authRights[userName] = [];
        }

        if (!authRights[userName].includes(permission)) {
          authRights[userName].push(permission);
        }
      });
    },

    async populateAuthRights(extraParamsJSON) {
      this.userAuthRights = {};
      this.groupAuthRights = {};

      const ownersFn = this.pick(authService.getClient(), [
        "getAuthorisedNames",
        "getAuthorizedNames",
        "listAuthorizedNames",
        "listOwnersForPermission",
        "getOwnersForPermission"
      ]);
      if (!ownersFn) return;

      this.permissions.forEach(permission => {
        ownersFn(permission, extraParamsJSON, handleThriftError(res => {
          this.addAuthRight(this.userAuthRights, permission, res.users || []);
          this.addAuthRight(this.groupAuthRights, permission, res.groups || []);
        }));
      });
    }
  }
};
