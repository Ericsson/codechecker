<template>
  <BaseProductPermission
    v-bind="$props"
    ref="basePermission"
    @update:error="$emit('update:error', $event)"
    @update:success="$emit('update:success', $event)"
    @update:auth-rights="$emit('update:authRights', $event)"
  />
</template>

<script setup>
import {
  ref
} from "vue";

import BaseProductPermission from "./BaseProductPermission";

defineProps({
  title: { type: String, default: "Group permissions" },
  label: { type: String, default: "Group name" },
  icon: { type: String, default: "mdi-account-group-outline" }
});

defineEmits([
  "update:error",
  "update:success",
  "update:authRights"
]);

defineOptions({
  name: "ProductGroupPermission"
});

const basePermission = ref(null);

defineExpose({
  saveAll: () => basePermission.value?.saveAll()
});

</script>
