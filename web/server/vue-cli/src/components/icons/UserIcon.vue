<template>
  <v-avatar
    :color="strToColor(value)"
    :title="value"
    :size="size"
    class="my-1"
    :tile="tile"
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
    value: { type: String, required: true },
    size: { type: Number, default: 48 },
    tile: { type: Boolean, default: false }
  },
  computed: {
    userIconName() {
      return this.value.charAt(0).toUpperCase();
    }
  }
};
</script>
