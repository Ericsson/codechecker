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
              v-for="permission in computedPermissions"
              :key="permission"
              class="text-center"
            >
              {{ permissionToString(permission) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(authRight, userName) in localAuthRights"
            :key="userName"
          >
            <td>
              <v-icon>
                {{ icon }}
              </v-icon>
              {{ userName }}
            </td>
            <td
              v-for="permission in computedPermissions"
              :key="permission"
              class="pa-1 text-center"
              width="1%"
            >
              <span class="d-inline-block">
                <v-checkbox
                  :input-value="authRight.includes(permission)"
                  :hide-details="true"
                  class="ma-1"
                  @change="() => toggle(userName, permission)"
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
      @keyup.enter="addNewAuthRight"
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
      changedAuthRights: {},
      localAuthRights: {}
    };
  },

  computed: {
    computedPermissions() {
      return this.permissions && this.permissions.length
        ? this.permissions
        : [ Permission.SUPERUSER, Permission.PERMISSION_VIEW ];
    }
  },

  watch: {
    authRights: {
      deep: true,
      immediate: true,
      handler(v) {
        this.localAuthRights = JSON.parse(JSON.stringify(v || {}));
      }
    }
  },

  mounted() {
    if (this.bus && this.bus.on) this.bus.on("save", this.saveAll);
  },

  beforeUnmount() {
    if (this.bus && this.bus.off) this.bus.off("save", this.saveAll);
  },

  methods: {
    permissionToString(value) {
      return Object.keys(Permission).find(key => Permission[key] === value);
    },

    toggle(userName, permission) {
      const cur = this.localAuthRights[userName] ? [ ...this.localAuthRights[userName] ] : [];
      const idx = cur.indexOf(permission);
      if (idx === -1) cur.push(permission); else cur.splice(idx, 1);
      this.localAuthRights = { ...this.localAuthRights, [userName]: cur };

      const orig = this.authRights[userName] || [];
      const nowHas = cur.includes(permission);
      const origHad = orig.includes(permission);

      if (nowHas === origHad) {
        const arr = this.changedAuthRights[userName] ? [ ...this.changedAuthRights[userName] ] : [];
        const i = arr.indexOf(permission);
        if (i !== -1) {
          arr.splice(i, 1);
          if (arr.length) {
            this.changedAuthRights = { ...this.changedAuthRights, [userName]: arr };
          } else {
            const { [userName]: _, ...rest } = this.changedAuthRights;
            this.changedAuthRights = rest;
          }
        }
      } else {
        const arr = this.changedAuthRights[userName] ? [ ...this.changedAuthRights[userName] ] : [];
        if (!arr.includes(permission)) arr.push(permission);
        this.changedAuthRights = { ...this.changedAuthRights, [userName]: arr };
      }
    },

    async saveAll() {
      const client = authService.getClient();
      const tasks = [];

      for (const userName of Object.keys(this.changedAuthRights)) {
        this.changedAuthRights[userName].forEach(permission => {
          tasks.push(new Promise(resolve => {
            const wantHas = (this.localAuthRights[userName] || []).includes(permission);
            const origHad = (this.authRights[userName] || []).includes(permission);

            if (wantHas === origHad) return resolve(true);

            const onDone = handleThriftError(success => {
              if (success) {
                if (wantHas) {
                  const list = this.localAuthRights[userName]
                    ? [ ...this.localAuthRights[userName] ] : [];
                  if (!list.includes(permission)) list.push(permission);
                  this.localAuthRights = { ...this.localAuthRights, [userName]: list };
                } else {
                  const list = [ ...(this.localAuthRights[userName] || []) ];
                  const idx = list.indexOf(permission);
                  if (idx !== -1) list.splice(idx, 1);
                  if (list.length) {
                    this.localAuthRights = { ...this.localAuthRights, [userName]: list };
                  } else {
                    const { [userName]: _, ...rest } = this.localAuthRights;
                    this.localAuthRights = rest;
                  }
                }
              }
              resolve(!!success);
            }, () => resolve(false));

            if (wantHas) {
              client.addPermission(permission, userName, this.isGroup, this.extraParamsJson, onDone);
            } else {
              client.removePermission(permission, userName, this.isGroup, this.extraParamsJson, onDone);
            }
          }));
        });
      }

      const results = await Promise.all(tasks);
      const ok = results.every(Boolean);
      this.$emit("update:success", ok);
      this.$emit("update:error", !ok);
      this.changedAuthRights = {};
    },


    addNewAuthRight() {
      if (!this.name.length) return;

      const searchKey = this.name.toLowerCase();
      const foundKey = Object.keys(this.localAuthRights).find(
        objectKey => objectKey.toLowerCase() === searchKey);

      if (!foundKey) {
        this.localAuthRights = { ...this.localAuthRights, [this.name]: [] };
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
ы