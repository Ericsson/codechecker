import { authService, handleThriftError } from "@cc-api";
import { PermissionFilter } from "@cc/auth-types";

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
    populatePermissions(scope, extraParamsJSON) {
      const filter = new PermissionFilter({ canManage: true });
      authService.getClient().getPermissionsForUser(scope, extraParamsJSON,
        filter, handleThriftError(permissions => {
          this.permissions = permissions;
          this.populateAuthRights(extraParamsJSON);
        }));
    },

    addAuthRight(authRights, permission, userNames) {
      userNames.forEach(userName => {
        if (!(userName in authRights)) {
          this.$set(authRights, userName, []);
        }

        if (!authRights[userName].includes(permission)) {
          authRights[userName].push(permission);
        }
      });
    },

    async populateAuthRights(extraParamsJSON) {
      this.userAuthRights = {};
      this.groupAuthRights = {};

      this.permissions.forEach(permission => {
        authService.getClient().getAuthorisedNames(permission,
          extraParamsJSON, handleThriftError(res => {
            this.addAuthRight(this.userAuthRights, permission, res.users);
            this.addAuthRight(this.groupAuthRights, permission, res.groups);
          }));
      });
    }
  }
};
