<template>
  <v-container fluid>
    <v-row justify="center">
      <v-col cols="auto">
        <ProductUserPermission
          ref="userPermission"
          :permissions="permissions"
          :auth-rights="userAuthRights"
          :extra-params-json="extraParamsJSON"
          :is-group="false"
          :success="success"
          :error="error"
          @update:success="success => emit('update:success', success)"
          @update:error="error => emit('update:error', error)"
          @update:auth-rights="authRights => userAuthRights = authRights"
        />
      </v-col>
      <v-col cols="auto">
        <ProductGroupPermission
          ref="groupPermission"
          :permissions="permissions"
          :auth-rights="groupAuthRights"
          :extra-params-json="extraParamsJSON"
          :is-group="true"
          :success="success"
          :error="error"
          @update:success="success => emit('update:success', success)"
          @update:error="error => emit('update:error', error)"
          @update:auth-rights="authRights => groupAuthRights = authRights"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { usePopulatePermissions } from "@/composables/usePopulatePermissions";
import {
  computed,
  onMounted,
  ref
} from "vue";
import ProductGroupPermission from "./ProductGroupPermission";
import ProductUserPermission from "./ProductUserPermission";

const props = defineProps({
  product: { type: Object, required: true },
  success: { type: Boolean, default: false },
  error: { type: Boolean, default: false }
});
const emit = defineEmits([
  "update:success",
  "update:error"
]);
const userPermission = ref(null);
const groupPermission = ref(null);

const {
  populatePermissions,
  userAuthRights,
  groupAuthRights,
  permissions
} = usePopulatePermissions();

const scope = "PRODUCT";
const extraParamsJSON = computed(() => JSON.stringify(
  { productID: props.product.id.toNumber() }
));

onMounted(() => {
  populatePermissions(scope, extraParamsJSON.value);
});

function savePermissions() {
  userPermission.value?.saveAll();
  groupPermission.value?.saveAll();
}

defineExpose({
  savePermissions
});
</script>
