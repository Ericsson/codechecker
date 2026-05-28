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
import { ref } from "vue";

import BaseProductPermission from "./BaseProductPermission";

defineProps({
  title: { type: String, default: "User permissions" },
  label: { type: String, default: "User name" }
});

defineEmits([
  "update:error",
  "update:success",
  "update:authRights"
]);

defineOptions({
  name: "ProductUserPermission"
});

const basePermission = ref(null);

defineExpose({
  saveAll: () => basePermission.value?.saveAll()
});

</script>
