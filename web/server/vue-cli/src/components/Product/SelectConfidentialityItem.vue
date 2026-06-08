<template>
  <div>
    <v-avatar
      left
      :size="16"
    >
      <confidentiality-icon
        :value="confidentialityFromStringToCode(value)"
        size="small"
      />
    </v-avatar>
    {{ value }}
  </div>
</template>

<script setup>
import { ConfidentialityIcon } from "@/components/Icons";
import { useConfidentiality } from "@/composables/useConfidentiality";

defineProps({
  value: { type: String, required: true }
});

const {
  confidentialityFromStringToCode 
} = useConfidentiality();

</script>

