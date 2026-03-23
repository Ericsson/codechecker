<template>
  <v-snackbar
    vertical
    color="error"
    :value="errors.length"
    :timeout="-1"
  >
    <v-alert
      v-for="(error, idx) in errors"
      :key="idx"
      type="error"
      color="white"
      density="compact"
      variant="outlined"
      text
    >
      {{ error }}
    </v-alert>

    <v-btn
      text
      @click="clearErrors"
    >
      Close
    </v-btn>
  </v-snackbar>
</template>

<script setup>
import { CLEAR_ERRORS } from "@/store/mutations.type";
import { computed } from "vue";
import { useStore } from "vuex";

const store = useStore();

const errors = computed(() => store.getters.errors);

const clearErrors = () => store.commit(CLEAR_ERRORS);
</script>