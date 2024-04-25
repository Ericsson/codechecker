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

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
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

<script>

import {
  CheckerInfoAvailability,
  setCheckerStatusUnavailableDueToVersion
} from "@/mixins/api/analysis-info-handling.mixin";

export default {
  name: "CheckerCoverageStatisticsDialog",

  props: {
    value: { type: Boolean, required: true },
    checkerName: { type: String, default: null },
    type: { type: String, required: true },
    runData: { type: Array, default: () => [] }
  },

  data() {
    return {
      runsWithAnalysisInfo: [],
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

    title() {
      let title = `${this.type.charAt(0).toUpperCase() 
        + this.type.slice(1)} run list`;
      if ( this.checkerName ) {
        title += ` for the "${this.checkerName}" checker`;
      }
      return title;
    },

    runs() {
      if (this.runData.length && this.runData[0].analysisInfo !== undefined) {
        const alertTypes = {
          [CheckerInfoAvailability.RunHistoryStoredWithOldVersionPre_v6_24]: {
            runNames: [],
            message: "analysed by an older version of CodeChecker. \
            The list of checker statistics are only available \
            from CodeChecker 6.24:"
          },
          [CheckerInfoAvailability.UnknownReason]: {
            runNames: [],
            message: "likely stored from a report directory \
            which was not created natively by CodeChecker analyze:"
          }
        };
        
        this.runData.map(run => {
          setCheckerStatusUnavailableDueToVersion(
            run.analysisInfo, run.codeCheckerVersion);
          
          alertTypes[run.analysisInfo.checkerInfoAvailability].runNames.push(
            run.runName);
        });

        return Object.values(alertTypes);
      }
      else {
        return [ { 
          runNames: this.runData.map(run => run.runName),
          message: null 
        } ];
      }
    }
  }
};
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

