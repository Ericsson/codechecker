<template>
  <v-btn
    class="toggle-blame-view-btn"
    color="primary"
    outlined
    small
    :disabled="disabled"
    @click="toggleBlameView"
  >
    <span v-if="value">
      <v-icon class="mr-1" small>mdi-text-box-outline</v-icon>
      Normal view
    </span>
    <span v-else>
      <v-icon class="mr-1" small>mdi-git</v-icon>
      Blame view
    </span>
  </v-btn>
</template>

<script>
export default {
  name: "ToggleBlameViewBtn",
  props: {
    value: { type: Boolean, required: true },
    disabled: { type: Boolean, default: false }
  },
  methods: {
    toggleBlameView() {
      this.$emit("input", !this.value);
    }
  }
};
</script>
