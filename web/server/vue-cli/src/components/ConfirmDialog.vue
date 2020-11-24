<template>
  <v-dialog
    v-model="dialog"
    persistent
    :content-class="contentClass"
    :max-width="maxWidth"
    :scrollable="scrollable"
  >
    <template v-slot:activator="{ on }">
      <slot name="activator" :on="on" />
    </template>

    <v-card
      v-if="loading"
      color="primary"
      dark
    >
      <v-card-text>
        Loading...
        <v-progress-linear
          indeterminate
          color="white"
          class="mb-0"
        />
      </v-card-text>
    </v-card>

    <v-card v-else>
      <v-card-title
        class="pt-3 pb-2 title primary white--text"
        primary-title
      >
        <slot name="title" />

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-progress-linear v-if="confirmInProgress" indeterminate />

      <v-card-text class="pa-0">
        <v-container fluid>
          <slot name="content" />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          class="cancel-btn"
          :color="cancelBtnColor"
          @click="dialog = false"
        >
          {{ cancelBtnLabel }}
        </v-btn>

        <v-btn
          text
          class="confirm-btn"
          :color="confirmBtnColor"
          @click="$emit('confirm')"
        >
          {{ confirmBtnLabel }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  name: "ConfirmDialog",
  props: {
    value: { type: Boolean, default: false },
    cancelBtnLabel: { type: String, default: "Cancel" },
    cancelBtnColor: { type: String, default: "error" },
    confirmBtnLabel: { type: String, default: "Save" },
    confirmBtnColor: { type: String, default: "primary" },
    confirmInProgress: { type: Boolean, default: false },
    maxWidth: { type: String, default: "600px" },
    scrollable: { type: Boolean, default: true },
    loading: { type: Boolean, default: false },
    contentClass: { type: String, default: null }
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit("input", value);
      }
    }
  }
};
</script>
