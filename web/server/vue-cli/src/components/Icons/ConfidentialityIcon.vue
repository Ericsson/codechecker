<template>
  <v-icon
    v-if="value === Confidentiality.CONFIDENTIAL"
    color="#ff0000"
    :title="title"
    :size="size"
    :small="small"
  >
    mdi-shield-lock-outline
  </v-icon>

  <v-icon
    v-else-if="value === Confidentiality.INTERNAL"
    color="#4e4e4e"
    :title="title"
    :size="size"
    :small="small"
  >
    mdi-shield-sun-outline
  </v-icon>

  <v-icon
    v-else-if="value === Confidentiality.OPEN"
    color="#669603"
    :title="title"
    :size="size"
    :small="small"
  >
    mdi-shield-sun-outline
  </v-icon>
</template>

<script>
import { Confidentiality } from "@cc/prod-types";
import { ConfidentialityMixin } from "@/mixins";

export default {
  name: "ConfidentialityIcon",
  mixins: [ ConfidentialityMixin ],
  props: {
    value: { type: Number, required: true },
    size: { type: Number, default: null },
    small: { type: Boolean, default: false }
  },

  data() {
    return {
      Confidentiality
    };
  },

  computed: {
    title() {
      return this.confidentialityFromCodeToString(this.value);
    }
  }
};
</script>
