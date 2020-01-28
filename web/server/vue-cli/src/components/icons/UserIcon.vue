<template>
  <v-avatar
    :color="strToColor(value)"
    size="48"
    class="my-1"
  >
    <span class="white--text headline">
      {{ userIconName }}
    </span>
  </v-avatar>
</template>

<script>
import { StrToColorMixin } from "@/mixins";

export default {
  name: "UserIcon",
  mixins: [ StrToColorMixin ],
  props: {
    value: { type: String, required: true }
  },
  computed: {
    userIconName() {
      return this.value.charAt(0).toUpperCase();
    }
  }
};
</script>
