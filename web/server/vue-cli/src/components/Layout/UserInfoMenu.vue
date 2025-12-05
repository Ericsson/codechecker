<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
  >
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        id="user-info-menu-btn"
        text
        class="text-none"
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
          <template v-slot:prepend>
            <user-icon
              :value="currentUser"
            />
          </template>

          <v-list-item-title class="headline">
            {{ currentUser }}
          </v-list-item-title>
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
              variant="outlined"
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

      <personal-access-token-btn />

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

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";

import { authService, handleThriftError } from "@cc-api";
import { PermissionFilter } from "@cc/auth-types";
import { Permission } from "@cc/shared-types";

import { UserIcon } from "@/components/Icons";
import PersonalAccessTokenBtn from "@/components/Layout/PersonalAccessTokenBtn";
import { GET_LOGGED_IN_USER, LOGOUT } from "@/store/actions.type";

const menu = ref(false);
const systemPermissions = ref([]);
const productPermissions = ref([]);
const permissionFilter = ref(new PermissionFilter({ given: true }));
const store = useStore();
const router = useRouter();

const permissions = computed(() => {
  return systemPermissions.value.concat(productPermissions.value);
});

const currentUser = computed(() => store.getters.currentUser);
const currentProduct = computed(() => store.getters.currentProduct);

watch(currentProduct, () => {
  if (!currentProduct.value) {
    productPermissions.value = [];
    return;
  }

  const extraParams = JSON.stringify({
    productID: currentProduct.value.id.toNumber()
  });

  authService.getClient().getPermissionsForUser("PRODUCT", extraParams,
    permissionFilter.value, handleThriftError(permissions => {
      productPermissions.value = permissions;
    }));
});

onMounted(() => {
  getLoggedInUser();
  fetchPermissions();
});

function fetchPermissions() {
  authService.getClient().getPermissionsForUser("SYSTEM",
    JSON.stringify({}), permissionFilter.value,
    handleThriftError(permissions => {
      systemPermissions.value = permissions;
    }));
}

function permissionFromCodeToString(permission) {
  for (const key in Permission)
    if (Permission[key] === permission)
      return key;
}

function logOut() {
  store.dispatch(LOGOUT).then(() => {
    router.push({ name: "login" });
    menu.value = false;
  });
}

function getLoggedInUser() {
  store.dispatch(GET_LOGGED_IN_USER);
}
</script>