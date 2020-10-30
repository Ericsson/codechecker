<template>
  <v-chip
    outlined
    small
  >
    <v-avatar
      class="mr-0"
      left
    >
      <v-icon
        :color="strToColor(value)"
        small
      >
        mdi-tag-outline
      </v-icon>
    </v-avatar>
    <span
      class="grey--text text--darken-3"
    >
      {{ value }}
    </span>
  </v-chip>
</template>

<script>
import { StrToColorMixin } from "@/mixins";

export default {
  name: "VersionTag",
  mixins: [ StrToColorMixin ],
  props: {
    value: { type: String, required: true }
  }
};
</script>
