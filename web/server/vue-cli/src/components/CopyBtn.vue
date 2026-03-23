<template>
  <v-tooltip
    v-model="copyInProgress"
    color="black"
    right
  >
    <template v-slot:activator="{}">
      <v-btn
        icon
        size="x-small"
        @click="copy"
      >
        <v-icon v-if="copyInProgress" color="green">
          mdi-check
        </v-icon>

        <v-icon v-else>
          mdi-content-paste
        </v-icon>    
      </v-btn>
    </template>
    Copied!
  </v-tooltip>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  value: { type: String, required: true }
});

const copyInProgress = ref(false);

async function writeToClipboard(str) {
  await navigator.clipboard.writeText(str);
}

async function copy() {
  copyInProgress.value = true;
  await writeToClipboard(props.value);
  setTimeout(() => copyInProgress.value = false, 1000);
}
</script>
