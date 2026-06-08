<template>
  <v-container>
    <h3 class="mb-4 text-center text-primary">
      {{ title }}
    </h3>
    <v-table
      height="200px"
      fixed-header
      density="compact"
    >
      <template v-slot:default>
        <thead>
          <tr>
            <th class="text-left">
              {{ label }}
            </th>
            <th
              v-for="permission in permissions"
              :key="permission"
              class="text-center"
            >
              {{ permissionToString(permission) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(authRight, userName) in authRights"
            :key="userName"
          >
            <td>
              <v-icon>
                {{ icon }}
              </v-icon>
              {{ userName }}
            </td>
            <td
              v-for="permission in permissions"
              :key="permission"
              class="pa-1 text-center"
              width="1%"
            >
              <span class="d-inline-block">
                <v-checkbox
                  :model-value="authRight.includes(permission)"
                  :hide-details="true"
                  class="ma-1"
                  @change="changeAuthPermission(userName, permission)"
                />
              </span>
            </td>
          </tr>
        </tbody>
      </template>
    </v-table>

    <v-text-field
      v-model="name"
      :label="label"
      hide-details
      variant="outlined"
      class="mt-4"
      @keyup.enter="addNewAuthRight"
    >
      <template v-slot:append-inner>
        <v-btn
          color="primary"
          class="ma-0"
          @click="addNewAuthRight"
        >
          Add
        </v-btn>
      </template>
    </v-text-field>
  </v-container>
</template>

<script setup>
import { ref } from "vue";

import { authService, handleThriftError } from "@cc-api";
import { Permission } from "@cc/shared-types";

const props = defineProps({
  permissions: { type: Array, default: () => [] },
  authRights: { type: Object, default: () => {} },
  title: { type: String, default: "" },
  label: { type: String, default: "" },
  icon: { type: String, default: "mdi-account-outline" },
  extraParamsJson: { type: String, required: true },
  isGroup: { type: Boolean, required: true }
});
const emit = defineEmits([
  "update:error",
  "update:success",
  "update:authRights"
]);
const name = ref("");
const changedAuthRights = ref({});

function permissionToString(value) {
  return Object.keys(Permission).find(key => Permission[key] === value);
}

function changeAuthPermission(userName, permission) {
  if (changedAuthRights.value[userName] &&
      changedAuthRights.value[userName].indexOf(permission) !== -1
  ) {
    // Removing a permission to the user.
    const ind = changedAuthRights.value[userName].indexOf(permission);
    changedAuthRights.value[userName].splice(ind, 1);

    // Remove the user from the changes if there is no more permissions.
    if (!changedAuthRights.value[userName].length) {
      delete changedAuthRights.value[userName];
    }
  } else {
    // Add new permission to the user.
    if (!(userName in changedAuthRights.value)) {
      changedAuthRights.value[userName] = [];
    }
    changedAuthRights.value[userName].push(permission);
  }
}

function saveAll() {
  for (const userName of Object.keys(changedAuthRights.value)) {
    changedAuthRights.value[userName].forEach(permission => {
      if (props.authRights[userName] &&
          props.authRights[userName].indexOf(permission) !== -1
      ) {
        authService.getClient().removePermission(permission, userName,
          props.isGroup, props.extraParamsJson,
          handleThriftError(success => {
            if (!success) {
              emit("update:error", true);
              return;
            }

            const updatedAuthRights = { ...props.authRights };
            const ind = updatedAuthRights[userName].indexOf(permission);
            updatedAuthRights[userName].splice(ind, 1);
            if (!updatedAuthRights[userName].length) {
              delete updatedAuthRights[userName];
            }
            emit("update:authRights", updatedAuthRights);
          }, () => {
            emit("update:error", true);
          }));
      } else {
        authService.getClient().addPermission(permission, userName,
          props.isGroup, props.extraParamsJson,
          handleThriftError(success => {
            if (!success) {
              emit("update:error", true);
              return;
            }

            const updatedAuthRights = { ...props.authRights };
            if (!(userName in updatedAuthRights)) {
              updatedAuthRights[userName] = [];
            }
            updatedAuthRights[userName].push(permission);
            emit("update:authRights", updatedAuthRights);
          }, () => {
            emit("update:error", true);
          }));
      }
    });
  }

  emit("update:success", true);

  changedAuthRights.value = {};
}

function addNewAuthRight() {
  if (!name.value.length) return;

  const searchKey = name.value.toLowerCase();
  const foundKey = Object.keys(props.authRights).find(
    objectKey => objectKey.toLowerCase() === searchKey);

  if (!foundKey) {
    const updatedAuthRights = { ...props.authRights };
    updatedAuthRights[name.value] = [];
    emit("update:authRights", updatedAuthRights);
  }

  name.value = "";
}

defineExpose({
  saveAll
});
</script>

<style lang="scss" scoped>
:deep(.v-input--selection-controls__input) {
  margin: 0;
}
</style>
