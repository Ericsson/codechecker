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
      dense
      outlined
      text
    >
      {{ error }}
    </v-alert>

    <v-btn
      dark
      text
      @click="clearErrors"
    >
      Close
    </v-btn>
  </v-snackbar>
</template>

<script>
import { mapGetters, mapMutations } from "vuex";
import { CLEAR_ERRORS } from "@/store/mutations.type";

export default {
  name: "Errors",
  computed: {
    ...mapGetters([
      "errors"
    ])
  },
  methods: {
    ...mapMutations([
      CLEAR_ERRORS
    ])
  }
};
</script>