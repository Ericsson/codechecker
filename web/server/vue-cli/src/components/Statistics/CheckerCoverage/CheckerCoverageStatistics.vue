<template>
  <v-container fluid>
    <checker-coverage-statistics-dialog
      v-if="type"
      :value.sync="showRuns[type]"
      :checker-name="selectedCheckerName"
      :type="type"
      :run-data="runData"
    />
    <v-row>
      <v-col>
        <h3 class="title primary--text mb-2">
          <v-btn
            color="primary"
            outlined
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon
            title="Reload statistics"
            color="primary"
            @click="fetchStatistics"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
          <tooltip-help-icon
            color="primary"
            size="x-large"
          >
            The tab shows all enabled checkers in the selected runs.
            <br><br>
            Please, first select runs in the left "Run/Tag Filter" menu.
            If the filter is empty all runs are selected.
            Specifying a run tag is not applied.
            <br><br>
            Please, note that this feature is available only for runs analysed
            natively with <strong>CodeChecker 6.24</strong> and above.
          </tooltip-help-icon>
        </h3>

        <v-alert
          icon="mdi-information"
          class="mt-2"
        >
          In this statistics only the "Run / Tag Filter" 
          and the "Unique reports" are effective.
        </v-alert>

        <div v-if="!problematicRuns.length">
          <checker-coverage-statistics-table
            :items="statistics"
            :loading="loading"
            @enabled-click="showingRuns"
          />
        </div>
        <div v-else>
          <v-alert
            v-if="noProperRun"
            icon="mdi-alert"
            class="mt-2"
            color="deep-orange"
            outlined
          >
            There is no proper run for <strong>checker coverage </strong>
            statistics. Please create a new run first that analysed
            natively with <strong>6.24</strong>
            or above version of CodeChecker!
          </v-alert>
          <v-alert
            v-else
            icon="mdi-alert"
            class="mt-2"
            color="deep-orange"
            outlined
          >
            The Checker coverage statistics is not available 
            for
            <span
              style="cursor: pointer; text-decoration: underline;"
              @click="showingRuns('problematic', null)"
            >
              <strong>some of</strong>
            </span>
            the selected runs.
            <br>
            Please modify the run filter or click the
            <span
              style="cursor: pointer; text-decoration: underline;"
              @click="cleanRunList"
            >
              <strong>restrict selection</strong>
            </span>
            button to get relevant statistics.
            <br>
          </v-alert>
          <checker-coverage-statistics-table
            :items="[]"
            :loading="loading"
          />
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
  ReviewStatusMixin,
  SeverityMixin,
  ToCSV
} from "@/mixins";
import { AnalysisInfoHandlingAPIMixin } from "@/mixins/api";
import { BaseStatistics } from "@/components/Statistics";
import CheckerCoverageStatisticsTable from "./CheckerCoverageStatisticsTable";
import CheckerCoverageStatisticsDialog from "./CheckerCoverageStatisticsDialog";
import {
  MAX_QUERY_SIZE,
  ReportFilter,
  RunFilter
} from "@cc/report-server-types";
import { ccService, handleThriftError } from "@cc-api";
import {
  CheckerInfoAvailability
} from "@/mixins/api/analysis-info-handling.mixin";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

export default {
  name: "CheckerCoverageStatistics",
  components: {
    CheckerCoverageStatisticsTable,
    CheckerCoverageStatisticsDialog,
    TooltipHelpIcon
  },
  mixins: [
    AnalysisInfoHandlingAPIMixin,
    BaseStatistics,
    ReviewStatusMixin,
    SeverityMixin,
    ToCSV
  ],

  data() {
    return {
      checker_stat: {},
      loading: false,
      noProperRun: false,
      problematicRuns: [],
      runs: null,
      runData: [],
      selectedCheckerName: null,
      showRuns: {
        enabled: false,
        disabled: false,
        problematic: false
      },
      statistics: [],
      type: null,
    };
  },

  computed: {
    actualRunNames() {
      return this.runs.filter(run => !this.problematicRuns.map(
        problematicRun => problematicRun.runId
      ).includes(run.runId)).map(run => run.runName);
    }
  },

  watch: {
    checker_stat(stat) {
      this.statistics = Object.keys(stat).map(checker_id => {
        return {
          checker: stat[checker_id].checkerName,
          severity: stat[checker_id].severity,
          enabledInAllRuns: stat[checker_id].disabled.length === 0
            ? 1
            : 0,
          enabledRunLength: stat[checker_id].enabled.length,
          disabledRunLength: stat[checker_id].disabled.length,
          closed: stat[checker_id].closed.toNumber(),
          outstanding: stat[checker_id].outstanding.toNumber(),
        };
      });
    },

    async runIds() {
      this.noProperRun = false;
    },

    "$route"() {
      if (this.runs && this.$route.query.run !== this.actualRunNames) {
        this.$router.go();
      }
    }
  },

  methods: {
    downloadCSV() {
      const data = [
        [
          "Checker Name", "Severity", "Status",
          "Closed Reports", "Outstanding Reports",
        ],
        ...this.statistics.map(stat => {
          return [
            stat.checker,
            this.severityFromCodeToString(stat.severity),
            stat.enabledInAllRuns
              ? "Enabled in all selected runs"
              : "Not enabled in all selected runs",
            stat.closed,
            stat.outstanding
          ];
        })
      ];

      this.toCSV(data, "codechecker_checker_coverage_statistics.csv");
    },

    async getRunData() {
      const limit = MAX_QUERY_SIZE;
      let offset = 0;
      
      const filter = new RunFilter({
        ids: this.runIds
      });

      const runCount = await new Promise(resolve => {
        ccService.getClient().getRunCount(
          filter, handleThriftError(runCnt => {
            resolve(runCnt.toNumber());
          }));
      });

      const runs = [];

      for ( offset; offset <= runCount; offset+=limit ) {
        const limitedRuns = await new Promise(resolve => {
          ccService.getClient().getRunData(
            filter, limit, offset, null, handleThriftError(runDataList => {
              resolve(runDataList.map(runData => ({
                runId: runData.runId,
                runName: runData.name,
                codeCheckerVersion: runData.codeCheckerVersion
              })));
            }));
        });
        runs.push(...limitedRuns);
      }
       
      return runs;
    },

    async fetchStatistics() {
      this.loading = true;

      await this.fetchProblematicRuns();

      const filter = new ReportFilter(this.reportFilter);

      this.checker_stat = await new Promise(resolve => {
        ccService.getClient().getCheckerStatusVerificationDetails(
          this.runIds,
          filter,
          handleThriftError(res => {
            resolve(res);
          }));
      });

      this.loading = false;
    },

    async fetchProblematicRuns() {
      this.loading = true;

      const runs = await this.getRunData();
      this.problematicRuns = (await Promise.all(
        runs.map(async runData => {
          var analysisInfo = await this.loadAnalysisInfo(
            runData.runId, null, null);

          if (analysisInfo.checkerInfoAvailability !=
          CheckerInfoAvailability.Available) {
            return {
              ...runData,
              analysisInfo: analysisInfo
            };
          } else {
            return null;
          }
        }))).filter(element => element !== null);
      
      this.runs = runs;
      this.loading = false;
    },

    showingRuns(type, checker_name) {
      this.type = type;
      this.selectedCheckerName = checker_name;
      if ( type === "problematic" ) {
        this.runData = this.problematicRuns;
      }
      else {
        const checker_id = Object.keys(this.checker_stat).find(checker_id =>
          this.checker_stat[checker_id].checkerName === checker_name
        );

        this.runData = this.checker_stat[checker_id][type].map(
          run_id => this.runs.find(
            runData => runData.runId.toNumber() === run_id.toNumber()
          )
        );
      }

      this.showRuns[type] = true;
    },

    cleanRunList() {
      if ( this.actualRunNames.length ){
        this.$router.replace({
          query: {
            ...this.$route.query,
            "run": this.actualRunNames
          }
        }).catch(() => {});
      }
      else {
        this.noProperRun = true;
      }
    }
  }
};
</script>
