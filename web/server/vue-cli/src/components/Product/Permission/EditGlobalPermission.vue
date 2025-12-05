<template>
  <v-container fluid>
    <v-alert
      v-model="success"
      dismissible
      color="success"
      border="start"
      elevation="2"
      colored-border
      icon="mdi-check"
    >
      Permission changes saved successfully!
    </v-alert>

    <v-alert
      v-model="error"
      dismissible
      color="error"
      border="start"
      elevation="2"
      colored-border
      icon="mdi-alert-outline"
    >
      Some permission changes could not be saved!
    </v-alert>

    <v-row>
      <v-col>
        <product-user-permission
          ref="userPermission"
          v-model:success="success"
          v-model:error="error"
          :permissions="permissions"
          :auth-rights="userAuthRights"
          :extra-params-json="extraParamsJSON"
          :is-group="false"
          @update:auth-rights="userAuthRights = $event"
        />
      </v-col>
      <v-col>
        <product-group-permission
          ref="groupPermission"
          v-model:success="success"
          v-model:error="error"
          :permissions="permissions"
          :auth-rights="groupAuthRights"
          :extra-params-json="extraParamsJSON"
          :is-group="true"
          @update:auth-rights="groupAuthRights = $event"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { usePopulatePermissions } from "@/composables/usePopulatePermissions";

import ProductGroupPermission from "./ProductGroupPermission";
import ProductUserPermission from "./ProductUserPermission";

const success = ref(false);
const error = ref(false);
const scope = ref("SYSTEM");
const extraParamsJSON = ref(JSON.stringify({}));
const userPermission = ref(null);
const groupPermission = ref(null);

const {
  populatePermissions,
  userAuthRights,
  groupAuthRights,
  permissions
} = usePopulatePermissions();

onMounted(() => {
  populatePermissions(scope.value, extraParamsJSON.value);
});

function saveAll() {
  userPermission.value?.saveAll();
  groupPermission.value?.saveAll();
}

defineExpose({
  saveAll
});
</script>
