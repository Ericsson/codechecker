<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="640px"
    :title="title"
    :icon="headerIcon"
    :buttons="false"
  >
    <template v-slot:content>
      <div class="statistics-dialog-content">
        <div class="run-count-summary mb-3">
          <v-chip
            :color="type === 'enabled' ? 'success' : 'error'"
            variant="tonal"
            size="small"
            label
          >
            {{ totalRunCount }}
            {{ totalRunCount === 1 ? "run" : "runs" }}
          </v-chip>
        </div>

        <div
          v-for="(run, groupIndex) in runs"
          :key="run.message || groupIndex"
          class="run-group"
        >
          <v-alert
            v-if="run.message && run.runNames.length"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-2"
          >
            {{ run.runNames.length > 1 ? "These runs are" : "This run is" }}
            {{ run.message }}
          </v-alert>

          <v-list
            class="run-list pa-0"
            density="compact"
            lines="one"
          >
            <v-list-item
              v-for="runName in run.runNames"
              :key="runName"
              class="run-list-item px-2"
            >
              <template v-slot:prepend>
                <v-icon
                  :color="type === 'enabled' ? 'success' : 'error'"
                  :icon="type === 'enabled' ? 'mdi-check-circle'
                    : 'mdi-close-circle'"
                  size="small"
                />
              </template>
              <v-list-item-title class="run-name">
                {{ runName }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </div>

        <div
          v-if="!totalRunCount"
          class="text-medium-emphasis text-center py-4"
        >
          No runs to display.
        </div>
      </div>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { computed } from "vue";
import {
  CheckerInfoAvailability,
  setCheckerStatusUnavailableDueToVersion,
} from "@/composables/useAnalysisInfo";
import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  checkerName: { type: String, default: null },
  type: { type: String, required: true },
  runData: { type: Array, default: () => [] }
});

const emit = defineEmits([ "update:modelValue" ]);

const dialog = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

const title = computed(function() {
  let _title = `${props.type.charAt(0).toUpperCase() 
    + props.type.slice(1)} run list`;
  if ( props.checkerName ) {
    _title += ` for the "${props.checkerName}" checker`;
  }
  return _title;
});

const headerIcon = computed(function() {
  return props.type === "enabled"
    ? "mdi-check-circle-outline"
    : "mdi-close-circle-outline";
});

const totalRunCount = computed(function() {
  return runs.value.reduce(
    (_sum, _run) => _sum + _run.runNames.length, 0);
});

const runs = computed(function() {
  if (props.runData.length && props.runData[0].analysisInfo !== undefined) {
    const _alertTypes = {
      [CheckerInfoAvailability.RunHistoryStoredWithOldVersionPre_v6_24]: {
        runNames: [],
        message: "analysed by an older version of CodeChecker. \
        The list of statistics are only available from CodeChecker 6.24:"
      },
      [CheckerInfoAvailability.UnknownReason]: {
        runNames: [],
        message: "likely stored from a report directory \
        which was not created natively by CodeChecker analyze:"
      }
    };
    
    props.runData.map(_run => {
      setCheckerStatusUnavailableDueToVersion(
        _run.analysisInfo, _run.codeCheckerVersion);
      
      _alertTypes[_run.analysisInfo.checkerInfoAvailability].runNames.push(
        _run.runName);
    });

    return Object.values(_alertTypes);
  }
  else {
    return [ { 
      runNames: props.runData.map(_run => _run.runName),
      message: null 
    } ];
  }
});
</script>

<style lang="scss" scoped>
.statistics-dialog-content {
  .run-group:not(:last-child) {
    margin-bottom: 12px;
  }

  .run-list {
    border: thin solid rgba(0, 0, 0, 0.12);
    border-radius: 6px;
    overflow: hidden;
  }

  .run-list-item:not(:last-child) {
    border-bottom: thin solid rgba(0, 0, 0, 0.06);
  }

  .run-name {
    font-size: 0.95rem;
  }
}
</style>

