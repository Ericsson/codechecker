import { ref } from "vue";

import { authService, handleThriftError } from "@cc-api";
import { PermissionFilter } from "@cc/auth-types";

export function usePopulatePermissions() {
  const permissions = ref([]);
  const userAuthRights = ref({});
  const groupAuthRights = ref({});

  function populatePermissions(scope, extraParamsJSON) {
    const filter = new PermissionFilter({ canManage: true });
    authService.getClient().getPermissionsForUser(scope, extraParamsJSON,
      filter, handleThriftError(_permissions => {
        permissions.value = _permissions;
        _populateAuthRights(extraParamsJSON);
      }));
  }

  function _addAuthRight(authRights, permission, userNames) {
    userNames.forEach(userName => {
      if (!(userName in authRights)) {
        authRights[userName] = [];
      }

      if (!authRights[userName].includes(permission)) {
        authRights[userName].push(permission);
      }
    });
  }

  function _populateAuthRights(extraParamsJSON) {
    userAuthRights.value = {};
    groupAuthRights.value = {};

    permissions.value.forEach(permission => {
      authService.getClient().getAuthorisedNames(permission,
        extraParamsJSON, handleThriftError(res => {
          _addAuthRight(userAuthRights.value, permission, res.users);
          _addAuthRight(groupAuthRights.value, permission, res.groups);
        }));
    });
  }

  return {
    permissions,
    userAuthRights,
    groupAuthRights,
    populatePermissions
  };
}
