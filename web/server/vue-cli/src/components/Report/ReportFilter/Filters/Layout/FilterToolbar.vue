<template>
  <v-expansion-panels
    v-model="panelOpen"
  >
    <v-expansion-panel
      eager
    >
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
            icon="mdi-close-circle"
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
  panelActive: { type: Boolean, default: false }
});

const emit = defineEmits([ "clear" ]);

const panelOpen = ref(undefined);

watch(() => props.panelActive, active => {
  panelOpen.value = active ? 0 : undefined;
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