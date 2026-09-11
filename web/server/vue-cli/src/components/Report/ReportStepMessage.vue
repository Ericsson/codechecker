<template>
  <v-card
    size="small"
    variant="flat"
    class="report-step-msg px-2"
    :color="color"
    :step-id="id"
    :type="type"
    :style="{ 'margin-left': marginLeft, color: textColor }"
    rounded="xs"
  >
    <v-card-text class="pa-0 d-flex align-center">
      <report-step-enum-icon
        class="report-step-enum mr-1"
        :type="type"
        :index="index"
      />

      <v-btn
        v-if="prevStep"
        variant="text"
        icon="mdi-chevron-left"
        size="small"
        density="compact"
        @click="showPrevReport"
      />

      <div class="flex-grow-1 flex-shrink-1 mx-3" style="min-width: 0;">
        <div class="text-body-2 text-wrap text-break">
          {{ value }}
        </div>
        <div
          v-if="!hideDocUrl && type === 'error'"
          class="text-caption"
        >
          <p v-if="docUrl" class="mb-0 text-caption">
            For more information see the
            <a
              class="show-documentation-btn text-primary"
              @click="showDocumentation"
            >
              checker documentation
            </a>.
          </p>
          <p
            v-else
            class="no-documentation-msg-text mb-0 text-caption text-grey"
          >
            No documentation for checker.
          </p>
        </div>
      </div>

      <v-btn
        v-if="nextStep"
        right
        variant="text"
        icon="mdi-chevron-right"
        size="small"
        density="compact"
        @click="showNextReport"
      />
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ReportStepEnumIcon } from "@/components/Icons";
import { getCssColor } from "@/utilities/colors";
import { computed } from "vue";

const props = defineProps({
  id: { type: [ String, Number ], required: true },
  value: { type: String, required: true },
  marginLeft: { type: String, default: "" },
  type: { type: String, default: null },
  index: { type: [ Number, String ], default: null },
  bus: { type: Object, default: null },
  prevStep: { type: Object, default: null },
  nextStep: { type: Object, default: null },
  docUrl: { type: String, default: null },
  hideDocUrl: { type: Boolean, default: false }
});

const color = computed(() => {
  switch (props.type) {
  case "error":
    return getCssColor("color-report-step-message-error-light");
  case "fixit":
    return getCssColor("color-report-step-message-fixit-light");
  case "macro":
    return getCssColor("color-report-step-message-macro-light");
  case "note":
    return getCssColor("color-report-step-message-note-light");
  default:
    return getCssColor("color-report-step-message-default-light");
  }
});

const textColor = computed(() => {
  switch (props.type) {
  case "error":
    return getCssColor("color-report-step-message-error");
  case "fixit":
    return getCssColor("color-report-step-message-fixit");
  case "macro":
    return getCssColor("color-report-step-message-macro");
  case "note":
    return getCssColor("color-report-step-message-note");
  default:
    return getCssColor("color-report-step-message-default");
  }
});

function showPrevReport() {
  if (props.prevStep && props.bus)
    props.bus.emit("jpmToPrevReport", props.prevStep);
}

function showNextReport() {
  if (props.nextStep && props.bus)
    props.bus.emit("jpmToNextReport", props.nextStep);
}

function showDocumentation() {
  window.open(props.docUrl, "_blank");
}
</script>

<style lang="scss">
.report-step-msg {
  padding-top: 10px !important;
  padding-bottom: 10px !important;
  margin-bottom: 2px;
  max-width: 640px;
  white-space: inherit;
  height: auto !important;
  border-radius: 12px !important;
  align-items: center !important;

  &.v-size--small {
    min-height: 24px;
    height: auto;

    .v-chip.report-step-enum {
      overflow: inherit;
    }

    .show-documentation-btn {
      border-bottom: 1px dashed var(--color-soft-blue);
      display: inline-block;
    }
  }
  .no-documentation-msg-text {
    color: grey
  }
}

.current {
  border: 2px dashed rgb(var(--v-theme-primary)) !important;
  opacity: 1;
  font-weight: bold;
}

.current[type="error"] {
  border: 2px dashed var(--color-report-step-message-error) !important;
}

.current[type="fixit"] {
  border: 2px dashed var(--color-report-step-message-fixit) !important;
}

.current[type="macro"] {
  border: 2px dashed var(--color-report-step-message-macro) !important;
}

.current[type="note"] {
  border: 2px dashed var(--color-report-step-message-macro) !important;
}
</style>
