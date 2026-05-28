<template>
  <v-dialog
    v-model="dialog"
    class="edit-source-component-dialog"
    max-width="600px"
    scrollable
  >
    <template v-slot:activator="{}">
      <slot />
    </template>

    <v-card
      :title="title"
    >
      <template v-slot:append>
        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </template>

      <v-card-text class="pa-0">
        <v-container>
          <v-form ref="form">
            <v-text-field
              v-model="nameInput"
              class="component-name"
              label="Name*"
              autofocus
              variant="outlined"
              required
              :rules="rules.name"
            />

            <v-textarea
              v-model="componentInput"
              class="component-value value"
              variant="outlined"
              required
              validate-on-blur
              label="Value"
              :placeholder="placeHolderValue"
              :rules="rules.value"
            />

            <v-textarea
              v-model="descriptionInput"
              class="component-description "
              label="Description"
              variant="outlined"
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
          variant="text"
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          class="save-btn"
          color="primary"
          variant="text"
          @click="saveSourceComponent"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ccService, handleThriftError } from "@cc-api";
import { computed, onMounted, ref } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  sourceComponent: { type: Object, default: () => null },
});

const emit = defineEmits([ "update:modelValue", "save:component" ]);

const title = computed(() => {
  return props.sourceComponent ?
    "Edit source component" : "New source component";
});


function isValidComponentValue (value) {
  const _lines = value.trim().split(/\r|\n/);
  for (let _i = 0; _i < _lines.length; ++_i) {
    if (!_lines[_i].startsWith("+") && !_lines[_i].startsWith("-") ||
         _lines[_i].trim().length < 2
    ) {
      return false;
    }
  }

  return true;
}

const form = ref(null);
const nameInput = ref(null);
const componentInput = ref(null);
const descriptionInput = ref(null);

const placeHolderValue = "Value of the source component.\nEach line must start "
                      + "with a \"+\" (results from this path should be "
                      + "listed) or a \"-\" (results from this path should "
                      + "not be listed) sign.\nFor whole directories, a "
                      + "trailing \"*\" must be added.\n"
                      + "E.g.: +/a/b/x.cpp or -/a/b/*";

const rules = {
  name: [ v => !!v || "Name is required" ],
  value: [
    v => !!v || "Value is required",
    v => isValidComponentValue(v) || "Component value format is "
      + "invalid! Every line should start with + or - sign followed by "
      + "one or more character."
  ]
};

const dialog = computed({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  }
});

onMounted(() => {
  if (props.sourceComponent) {
    nameInput.value = props.sourceComponent.name;
    componentInput.value = props.sourceComponent.value;
    descriptionInput.value = props.sourceComponent.description;
  }
});

async function saveSourceComponent() {
  const { valid } = await form.value.validate();
  if (!valid) return;

  if (props.sourceComponent &&
    props.sourceComponent.name !== nameInput.value)
  {
    await ccService.getClient().removeSourceComponent(
      props.sourceComponent.name, handleThriftError);
  }
  ccService.getClient().addSourceComponent(
    nameInput.value,
    componentInput.value,
    descriptionInput.value,
    handleThriftError(success => {
      if (success) {
        emit("save:component");
        dialog.value = false;
      }
    }));
}
</script>

<style lang="scss">
.value textarea::placeholder {
  opacity: 0.5;
}
</style>