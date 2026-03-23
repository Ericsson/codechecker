<template>
  <v-icon
    v-if="value === Confidentiality.CONFIDENTIAL"
    color="#ff0000"
    :title="title"
    :size="size"
  >
    mdi-shield-lock-outline
  </v-icon>

  <v-icon
    v-else-if="value === Confidentiality.INTERNAL"
    color="#4e4e4e"
    :title="title"
    :size="size"
  >
    mdi-shield-sun-outline
  </v-icon>

  <v-icon
    v-else-if="value === Confidentiality.OPEN"
    color="#669603"
    :title="title"
    :size="size"
  >
    mdi-shield-sun-outline
  </v-icon>
</template>

<script setup>
import { useConfidentiality } from "@/composables/useConfidentiality";
import { Confidentiality } from "@cc/prod-types";
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, required: true },
  size: { type: Number, default: null }
});

const confidentiality = useConfidentiality();

const title = computed(
  () => confidentiality.confidentialityFromCodeToString(props.value)
);
</script>
