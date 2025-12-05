<template>
  <v-btn
    class="toggle-blame-view-btn"
    color="primary"
    variant="outlined"
    size="small"
    :disabled="disabled"
    @click="toggleBlameView"
  >
    <span v-if="modelValue">
      <v-icon
        class="mr-1"
        size="small"
      >mdi-text-box-outline</v-icon>
      Normal view
    </span>
    <span v-else>
      <v-icon
        class="mr-1"
        size="small"
      >mdi-git</v-icon>
      Blame view
    </span>
  </v-btn>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  disabled: { type: Boolean, default: false }
});

const emit = defineEmits([ "update:modelValue" ]);

function toggleBlameView() {
  emit("update:modelValue", !props.modelValue);
}
</script>
