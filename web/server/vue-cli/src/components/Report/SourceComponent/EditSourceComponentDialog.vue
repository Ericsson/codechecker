<template>
  <v-dialog
    v-model="dialog"
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
        <span
          v-if="sourceComponent"
        >
          Edit source component
        </span>
        <span
          v-else
        >
          New source component
        </span>

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-text-field
            v-model="component.name"
            label="Name*"
            outlined
            required
          />

          <v-textarea
            v-model="component.value"
            class="value"
            outlined
            label="Value"
            :placeholder="placeHolderValue"
            required
          />

          <v-text-field
            v-model="component.description"
            label="Description"
            outlined
          />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          text
          @click="saveSourceComponent"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService } from "@cc-api";
import { SourceComponentData } from "@cc/report-server-types";

export default {
  name: "NewSourceComponentDialog",
  props: {
    value: { type: Boolean, default: false },
    sourceComponent: { type: Object, default: () => null },
  },
  data() {
    return {
      placeHolderValue: "Value of the source component.\nEach line must start "
                      + "with a \"+\" (results from this path should be "
                      + "listed) or a \"-\" (results from this path should "
                      + "not be listed) sign.\nFor whole directories, a "
                      + "trailing \"*\" must be added.\n"
                      + "E.g.: +/a/b/x.cpp or -/a/b/*"
    };
  },
  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    },

    component() {
      return new SourceComponentData(this.sourceComponent);
    }
  },

  methods: {
    saveSourceComponent() {
      const component = this.component;
      ccService.getClient().addSourceComponent(component.name,
      component.value, component.description, (/* err, success */) => {
        this.$emit("save:component");
        this.dialog = false;
      });
    }
  }
};
</script>

<style lang="sass">
.value textarea::placeholder {
  opacity: 0.5;
}
</style>