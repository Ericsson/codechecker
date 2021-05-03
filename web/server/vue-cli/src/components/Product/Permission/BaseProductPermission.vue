<template>
  <v-container>
    <h3 class="mb-4 text-center primary--text">
      {{ title }}
    </h3>
    <v-simple-table
      height="200px"
      fixed-header
      dense
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
                  :input-value="authRight.includes(permission)"
                  :hide-details="true"
                  class="ma-1"
                  @change="changeAuthPermission(userName, permission)"
                />
              </span>
            </td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>

    <v-text-field
      v-model="name"
      :label="label"
      single-line
      hide-details
      solo
      flat
      outlined
      class="mt-4"
      @keyup.native.enter="addNewAuthRight"
    >
      <template v-slot:append>
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

<script>
import { authService, handleThriftError } from "@cc-api";
import { Permission } from "@cc/shared-types";

export default {
  name: "BaseProductPermission",
  props: {
    permissions: { type: Array, default: () => [] },
    authRights: { type: Object, default: () => {} },
    title: { type: String, default: "" },
    label: { type: String, default: "" },
    icon: { type: String, default: "mdi-account-outline" },
    bus: { type: Object, required: true },
    extraParamsJson: { type: String, required: true },
    isGroup: { type: Boolean, required: true }
  },
  data() {
    return {
      Permission,
      name: "",
      changedAuthRights: {}
    };
  },

  mounted() {
    this.bus.$on("save", this.saveAll);
  },

  methods: {
    permissionToString(value) {
      return Object.keys(Permission).find(key => Permission[key] === value);
    },

    changeAuthPermission(userName, permission) {
      if (this.changedAuthRights[userName] &&
          this.changedAuthRights[userName].indexOf(permission) !== -1
      ) {
        // Removing a permission to the user.
        const ind = this.changedAuthRights[userName].indexOf(permission);
        this.changedAuthRights[userName].splice(ind, 1);

        // Remove the user from the changes if there is no more permissions.
        if (!this.changedAuthRights[userName].length) {
          delete this.changedAuthRights[userName];
        }
      } else {
        // Add new permission to the user.
        if (!(userName in this.changedAuthRights)) {
          this.changedAuthRights[userName] = [];
        }
        this.changedAuthRights[userName].push(permission);
      }
    },

    saveAll() {
      for (const userName of Object.keys(this.changedAuthRights)) {
        this.changedAuthRights[userName].forEach(permission => {
          if (this.authRights[userName] &&
              this.authRights[userName].indexOf(permission) !== -1
          ) {
            authService.getClient().removePermission(permission, userName,
              this.isGroup, this.extraParamsJson,
              handleThriftError(success => {
                if (!success) {
                  this.$emit("update:error", true);
                  return;
                }

                const ind = this.authRights[userName].indexOf(permission);
                this.authRights[userName].splice(ind, 1);
                if (!this.authRights[userName].length) {
                  delete this.authRights[userName];
                }
              }, () => {
                this.$emit("update:error", true);
              }));
          } else {
            authService.getClient().addPermission(permission, userName,
              this.isGroup, this.extraParamsJson,
              handleThriftError(success => {
                if (!success) {
                  this.$emit("update:error", true);
                  return;
                }

                if (!(userName in this.authRights)) {
                  this.authRights[userName] = [];
                }
                this.authRights[userName].push(permission);
              }, () => {
                this.$emit("update:error", true);
              }));
          }
        });
      }

      this.$emit("update:success", true);

      // Reset the store of changes.
      this.changedAuthRights = {};
    },

    addNewAuthRight() {
      if (!this.name.length) return;

      const searchKey = this.name.toLowerCase();
      const foundKey = Object.keys(this.authRights).find(
        objectKey => objectKey.toLowerCase() === searchKey);

      if (!foundKey) {
        this.$set(this.authRights, this.name, []);
      }

      this.name = "";
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-input--selection-controls__input {
  margin: 0;
}
</style>
