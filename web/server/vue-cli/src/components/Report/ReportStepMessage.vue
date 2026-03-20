<template>
  <v-chip
    size="small"
    variant="flat"
    class="report-step-msg"
    :color="color"
    :step-id="id"
    :type="type"
    :style="{ 'margin-left': marginLeft, color: textColor }"
    :title="value"
    rounded="xs"
  >
    <div class="d-flex align-center ga-2">
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

      <div>
        <div>{{ value }}</div>
        <div v-if="!hideDocUrl && type === 'error'">
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
    </div>
  </v-chip>
</template>

<script setup>
import { ReportStepEnumIcon } from "@/components/Icons";
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
    return "#f2dede";
  case "fixit":
    return "#fcf8e3";
  case "macro":
    return "#d7dac2";
  case "note":
    return "#d7d7d7";
  default:
    return "#bfdfe9";
  }
});

const textColor = computed(() => {
  switch (props.type) {
  case "error":
    return "#a94442";
  case "fixit":
    return "#8a6d3b";
  case "macro":
    return "#4f5c6d";
  case "note":
    return "#4f5c6d";
  default:
    return "#00546f";
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
      border-bottom: 1px dashed #438ec7;
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
</style>
