<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
    scrollable
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Analyzer statistics

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-expansion-panels
            v-model="activeExpansionPanels"
            multiple
            hover
          >
            <v-expansion-panel
              v-for="(stats, analyzer) in analyzerStatistics"
              :key="analyzer"
            >
              <v-expansion-panel-header
                class="pa-0 px-1 primary--text"
              >
                <b>{{ analyzer }}</b>
              </v-expansion-panel-header>

              <v-expansion-panel-content class="pa-1">
                <v-container>
                  <v-row>
                    <v-icon class="mr-2">
                      mdi-alpha-v-circle-outline
                    </v-icon>
                    <b class="pr-1">Version:</b> {{ stats.version }}
                  </v-row>
                  <v-row>
                    <analyzer-statistics-icon
                      value="successful"
                      class="mr-2"
                    />
                    <b class="pr-1">Number of successfully analyzed files:</b>
                    <v-chip
                      color="success"
                      dark
                      small
                    >
                      {{ stats.successful }}
                    </v-chip>
                  </v-row>
                  <v-row>
                    <analyzer-statistics-icon
                      value="failed"
                      class="mr-2"
                    />
                    <b class="pr-1">Number of files which failed to analyze:</b>
                    <v-chip
                      color="error"
                      dark
                      small
                    >
                      {{ stats.failed }}
                    </v-chip>
                  </v-row>
                  <v-row v-if="stats.failed">
                    <v-icon class="mr-2">
                      mdi-text-box-multiple-outline
                    </v-icon>
                    <b>Files which failed to analyze:</b>
                    <v-container class="pl-8">
                      <v-row>
                        <ul>
                          <li
                            v-for="file in stats.failedFilePaths"
                            :key="file"
                          >
                            {{ file }}
                          </li>
                        </ul>
                      </v-row>
                    </v-container>
                  </v-row>
                </v-container>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          @click="dialog = false"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { AnalyzerStatisticsIcon } from "@/components/Icons";

export default {
  name: "AnalyzerStatisticsDialog",
  components: {
    AnalyzerStatisticsIcon
  },
  props: {
    value: { type: Boolean, default: false },
    runId: { type: Object, default: () => null },
    runHistoryId: { type: Object, default: () => null }
  },

  data() {
    return {
      analyzerStatistics: null,
      activeExpansionPanels: []
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
    }
  },

  watch: {
    runId() {
      this.getAnalysisStatistics();
    },
    runHistoryId() {
      this.getAnalysisStatistics();
    }
  },

  mounted() {
    this.getAnalysisStatistics();
  },

  methods: {
    getAnalysisStatistics() {
      if (!this.dialog && !this.runId && !this.runHistoryId) return;

      ccService.getClient().getAnalysisStatistics(this.runId,
        this.runHistoryId, handleThriftError(stats => {
          this.analyzerStatistics = stats;

          // Open all expansion panel.
          this.activeExpansionPanels = [ ...Array(
            Object.keys(stats).length).keys() ];
        }));
    }
  }
};
</script>
