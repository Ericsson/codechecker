<template>
  <v-expansion-panels
    v-model="value"
  >
    <v-expansion-panel>
      <v-expansion-panel-title
        class="pa-0"
        hide-actions
      >
        <template #default="{ expanded }">
          <v-icon class="expansion-btn">
            {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>

          <slot name="prepend-toolbar-title" />

          <span
            class="
              text-body-2
              font-weight-semibold
              mr-2
              text-truncate"
          >{{ title }}</span>

          <slot name="append-toolbar-title" />

          <v-spacer />

          <slot name="prepend-toolbar-items" />

          <v-btn
            icon="mdi-delete"
            size="small"
            variant="plain"
            @click.stop="emit('clear');"
          />

          <slot name="append-toolbar-items" />
        </template>
      </v-expansion-panel-title>

      <v-expansion-panel-text>
        <slot />
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  title: { type: String, required: true },
  panel: { type: Boolean, default: false }
});

const emit = defineEmits([ "clear" ]);

const value = ref(null);

watch(() => props.panel, newPanel => {
  value.value = newPanel ? 0 : null;
}, { immediate: true });
</script>

<style lang="scss" scoped>
:deep(.v-toolbar > .v-toolbar__content) {
  padding: 0;
}

:deep(.selected-items) {
  color: grey;
}
</style>