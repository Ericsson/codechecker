<template>
  <v-list-item
    class="my-1 ml-7"
    density="compact"
  >
    <template v-slot:prepend>
      <v-switch
        hide-details
        density="compact"
        :model-value="modelValue"
        @update:model-value="(value) => emit('update:modelValue', value)"
      />
    </template>
    <v-list-item-title
      class="ml-2"
    >
      <span>
        Anywhere on report path
        <TooltipHelpIcon>
          In case of file-related filters only reports ending in those files
          are queried. With this option all reports return where the given
          files are involved anywhere on the bugpath.
        </TooltipHelpIcon>
      </span>
    </v-list-item-title>
  </v-list-item>
</template>

<script setup>
import TooltipHelpIcon from "@/components/TooltipHelpIcon.vue";

defineProps({
  modelValue: { type: Boolean, required: true }
});

const emit = defineEmits([ "update:modelValue" ]);

</script>