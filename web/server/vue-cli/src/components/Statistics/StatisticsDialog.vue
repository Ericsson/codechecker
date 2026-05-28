<template>
  <v-dialog
    v-model="dialog"
    content-class="documentation-dialog"
    max-width="70%"
    scrollable
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        {{ title }}

        <v-spacer />

        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

      <v-card-text>
        <div 
          v-for="run in runs"
          :key="run.message"
        >
          <div class="font-alert-message">
            <span 
              v-if="run.message && run.runNames.length"
            >
              {{ run.runNames.length > 1 ? "These runs are": "This run is" }}
              {{ run.message }}
            </span>
          </div>
          <v-container class="checker-rows-in-columns">
            <v-row
              v-for="runName in run.runNames"
              :key="runName"
              no-gutters
              align="center"
            >
              <v-col cols="auto" align-self="center">
                <v-icon 
                  v-if="type == 'enabled'"
                  class="mr-1"
                  color="success"
                >
                  mdi-check 
                </v-icon>
                <v-icon 
                  v-else
                  class="mr-1"
                  color="error"
                >
                  mdi-close
                </v-icon>
              </v-col>
              <v-col
                col="auto"
                align-self="center" 
                style="font-size: larger;"
              >
                {{ runName }}
              </v-col>
            </v-row>
          </v-container>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from "vue";
import {
  CheckerInfoAvailability,
  setCheckerStatusUnavailableDueToVersion,
} from "@/composables/useAnalysisInfo";

const props = defineProps({
  value: { type: Boolean, required: true },
  checkerName: { type: String, default: null },
  type: { type: String, required: true },
  runData: { type: Array, default: () => [] }
});

const emit = defineEmits([ "update:value" ]);

const dialog = computed({
  get() {
    return props.value;
  },
  set(val) {
    emit("update:value", val);
  }
});

const title = computed(function() {
  let _title = `${props.type.charAt(0).toUpperCase() 
    + props.type.slice(1)} run list`;
  if ( props.checkerName ) {
    _title += ` for the "${props.checkerName}" checker`;
  }
  return _title;
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
.checker-rows-in-columns {
  columns: 32em auto;
}
.font-alert-message {
  margin-top: 10px;
  font-size: 125%;
  font-weight: bold;
}
</style>

