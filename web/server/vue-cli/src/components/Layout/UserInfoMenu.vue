<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
  >
    <template v-slot:activator="{ on }">
      <v-btn
        id="user-info-menu-btn"
        text
        class="text-none"
        v-on="on"
      >
        <user-icon
          v-if="currentUser"
          :value="currentUser"
          :size="24"
          class="mr-2"
          txt-class="font-weight-bold white--text"
        />
        {{ currentUser }}
      </v-btn>
    </template>

    <v-card>
      <v-list>
        <v-list-item>
          <v-list-item-avatar>
            <user-icon
              :value="currentUser"
            />
          </v-list-item-avatar>

          <v-list-item-content>
            <v-list-item-title class="headline">
              {{ currentUser }}
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-card flat>
        <v-card-text>
          Permissions:
          <span v-if="permissions.length">
            <v-chip
              v-for="permission in permissions"
              :key="permission"
              class="ma-2"
              color="success"
              outlined
            >
              {{ permissionFromCodeToString(permission) }}
            </v-chip>
          </span>
          <span v-else>
            No permission
          </span>
        </v-card-text>
      </v-card>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          id="logout-btn"
          color="primary"
          text
          @click="logOut"
        >
          Log out
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script>
import { mapActions, mapGetters } from "vuex";

import { authService, handleThriftError } from "@cc-api";
import { PermissionFilter } from "@cc/auth-types";
import { Permission } from "@cc/shared-types";

import { UserIcon } from "@/components/Icons";
import { GET_LOGGED_IN_USER, LOGOUT } from "@/store/actions.type";

export default {
  name: "UserInfoMenu",
  components: {
    UserIcon
  },
  data() {
    return {
      menu: false,
      systemPermissions: [],
      productPermissions: [],
      permissionFilter: new PermissionFilter({ given: true })
    };
  },

  computed: {
    ...mapGetters([
      "currentUser",
      "currentProduct"
    ]),
    permissions() {
      return this.systemPermissions.concat(this.productPermissions);
    }
  },

  watch: {
    currentProduct() {
      if (!this.currentProduct) {
        this.productPermissions = [];
        return;
      }

      const extraParams = JSON.stringify({
        productID: this.currentProduct.id.toNumber()
      });

      authService.getClient().getPermissionsForUser("PRODUCT", extraParams,
        this.permissionFilter, handleThriftError(permissions => {
          this.productPermissions = permissions;
        }));
    }
  },


  mounted() {
    this.getLoggedInUser();
    this.fetchPermissions();
  },

  methods: {
    ...mapActions([
      GET_LOGGED_IN_USER
    ]),

    fetchPermissions() {
      authService.getClient().getPermissionsForUser("SYSTEM",
        JSON.stringify({}), this.permissionFilter,
        handleThriftError(permissions => {
          this.systemPermissions = permissions;
        }));
    },

    permissionFromCodeToString(permission) {
      for (const key in Permission)
        if (Permission[key] === permission)
          return key;
    },

    logOut() {
      this.$store
        .dispatch(LOGOUT)
        .then(
          () => {
            this.$router.push({ name: "login" });
            this.menu = false;
          });
    }
  }
};
</script>