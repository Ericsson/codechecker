<template>
  <v-avatar
    :color="color.strToColor(value)"
    :title="value"
    :size="size"
    class="my-1"
    :tile="tile"
  >
    <span :class="txtClass">
      {{ userIconName }}
    </span>
  </v-avatar>
</template>

<script setup>
import { computed } from "vue";
import { useStrToColor } from "@/composables/useStrToColor";

const props = defineProps({
  value: { type: String, required: true },
  size: { type: Number, default: 48 },
  tile: { type: Boolean, default: false },
  txtClass: { type: String, default: "font-weight-bold white--text title" },
});

const color = useStrToColor();

const userIconName = computed(
  () => (props.value || "?").charAt(0).toUpperCase()
);
</script>
