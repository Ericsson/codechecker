<template>
  <v-dialog
    v-model="dialog"
    content-class="edit-source-component-dialog"
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

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-form ref="form">
            <v-text-field
              v-model.trim="component.name"
              class="component-name"
              label="Name*"
              autofocus
              outlined
              required
              :rules="rules.name"
            />

            <v-textarea
              v-model.trim="component.value"
              class="component-value value"
              outlined
              required
              validate-on-blur
              label="Value"
              :placeholder="placeHolderValue"
              :rules="rules.value"
            />

            <v-textarea
              v-model.trim="component.description"
              class="component-description "
              label="Description"
              outlined
            />
          </v-form>
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          class="cancel-btn"
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          class="save-btn"
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
import { ccService, handleThriftError } from "@cc-api";
import { SourceComponentData } from "@cc/report-server-types";

function isValidComponentValue (value) {
  const lines = value.trim().split(/\r|\n/);
  for (let i = 0; i < lines.length; ++i) {
    if (!lines[i].startsWith("+") && !lines[i].startsWith("-") ||
         lines[i].trim().length < 2
    ) {
      return false;
    }
  }

  return true;
}

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
                      + "E.g.: +/a/b/x.cpp or -/a/b/*",
      rules: {
        name: [ v => !!v || "Name is required" ],
        value: [
          v => !!v || "Value is required",
          v => isValidComponentValue(v) || "Component value format is "
            + "invalid! Every line should start with + or - sign followed by "
            + "one or more character."
        ]
      }
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
    async saveSourceComponent() {
      if (!this.$refs.form.validate()) return;

      // Remove the original component because the user would like to change
      // the name.
      if (this.sourceComponent &&
          this.sourceComponent.name !== this.component.name
      ) {
        await ccService.getClient().removeSourceComponent(
          this.sourceComponent.name, handleThriftError);
      }

      const component = this.component;
      ccService.getClient().addSourceComponent(component.name,
        component.value, component.description,
        handleThriftError(success => {
          if (success) {
            this.$emit("save:component");
            this.dialog = false;
          }
          // TODO: handle case when success is false.
        }));
    }
  }
};
</script>

<style lang="scss">
.value textarea::placeholder {
  opacity: 0.5;
}
</style>