<template>
  <v-dialog
    v-model="dialog"
    content-class="remove-source-component-dialog"
    max-width="600px"
    scrollable
  >
    <template v-slot:activator="{}">
      <slot />
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Remove source component

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container
          v-if="sourceComponent"
        >
          Are you sure that you would like to remove
          <b>{{ sourceComponent.name }}</b> source component?
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          class="cancel-btn"
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="error"
          text
          class="remove-btn"
          @click="removeSourceComponent"
        >
          Remove
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "RemoveSourceComponentDialog",
  props: {
    value: { type: Boolean, default: false },
    sourceComponent: { type: Object, default: () => null }
  },

  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    }
  },

  methods: {
    removeSourceComponent() {
      ccService.getClient().removeSourceComponent(this.sourceComponent.name,
        handleThriftError(success => {
          if (success) {
            this.$emit("on:confirm");
            this.dialog = false;
          }
          // TODO: handle cases when success is false.
        }));
    }
  }
};
</script>
