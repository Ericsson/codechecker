<template>
  <v-dialog
    v-model="dialog"
    content-class="documentation-dialog"
    max-width="600px"
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Checker documentation

        <v-spacer />

        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

      <v-card-text>
        <v-container>
          <p v-if="labels.length === 0" class="pt-4">
            <strong>No documentation to this checker.</strong>
          </p>
          <v-row
            v-for="val in formattedLabels"
            v-else
            :key="val[0]"
          >
            <v-col cols="4" align-self="center">
              <strong>{{ formatLabel(val[0]) }}</strong>
            </v-col>
            <v-col>
              <severity-icon
                v-if="val[0] === 'severity'"
                :status="val[1]"
              />
              <a
                v-else-if="val[0] === 'doc_url' && val[1] !== 'Not available'"
                :href="val[1]"
                target="_blank"
              >
                {{ val[1] }}
              </a>
              <span v-else>
                {{ val[1] }}
              </span>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { SeverityIcon } from "@/components/Icons";
import { ccService, handleThriftError } from "@cc-api";
import { Checker, Severity } from "@cc/report-server-types";
import { computed, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  checker: { type: Checker, default: null }
});

const emit = defineEmits([ "update:modelValue" ]);

const labels = ref([]);

const dialog = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

const formattedLabels = computed(() => {
  const result = {};

  for (const label of labels.value) {
    const pos = label.indexOf(":");
    const key = label.substring(0, pos);
    const value = label.substring(pos + 1);

    if (key in result)
      result[key].push(value);
    else
      result[key] = [ value ];
  }

  if ("severity" in result)
    result["severity"] = Severity[result["severity"][0]];

  result["doc_url"] =
    "doc_url" in result ? result["doc_url"][0] : "Not available";

  for (const key in result) {
    if (Array.isArray(result[key]))
      result[key] = result[key].join(", ");
  }

  return Object.entries(result).sort();
});

watch(() => props.modelValue, () => {
  getCheckerDoc();
});

function getCheckerDoc() {
  ccService.getClient().getCheckerLabels([ props.checker ],
    handleThriftError(labels => labels.value = labels[0]));
}

function formatLabel(key) {
  switch (key) {
  case "profile":
    return "Profile";
  case "severity":
    return "Severity";
  case "doc_url":
    return "Documentation URL";
  case "guideline":
    return "Covered guideline";
  default:
    return key;
  }
}
</script>
