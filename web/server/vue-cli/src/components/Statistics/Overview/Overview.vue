<template>
  <v-container fluid>
    <reports
      :bus="bus"
      :run-ids="runIds"
      :report-filter="reportFilter"
    />

    <v-row>
      <v-col>
        <single-line-widget
          icon="mdi-close"
          color="red"
          label="Number of failed files"
          :bus="bus"
          :get-value="getNumberOfFailedFiles"
        >
          <template #help>
            Number of failed files in the current product.<br><br>
            Only the Run filter will affect this value.
          </template>

          <template #value="{ value }">
            <failed-files-dialog>
              <template #default="{ on }">
                <span class="num-of-failed-files" v-on="on">
                  {{ value }}
                </span>
              </template>
            </failed-files-dialog>
          </template>
        </single-line-widget>
      </v-col>

      <v-col>
        <single-line-widget
          icon="mdi-card-account-details"
          color="grey"
          label="Number of checkers reporting faults"
          :bus="bus"
          :get-value="getNumberOfActiveCheckers"
        >
          <template #help>
            Number of checkers which found some report in the current
            product.<br><br>

            Every filter will affect this value.
          </template>
        </single-line-widget>
      </v-col>
    </v-row>

    <v-row class="my-4">
      <v-col>
        <v-card flat>
          <v-card-title class="justify-center">
            Number of outstanding reports

            <tooltip-help-icon>
              Shows the number of reports which were active in the last
              <i>x</i> months/days.<br><br>

              Reports marked as <b>False positive</b> or <b>Intentional</b>
              will be <i>excluded</i> from these numbers.<br><br>

              The following filters don't affect these values:
              <ul>
                <li><b>Outstanding reports on a given date</b> filter.</li>
                <li>All filters in the <b>COMPARE TO</b> section.</li>
                <li><b>Latest Review Status</b> filter.</li>
                <li><b>Latest Detection Status</b> filter.</li>
              </ul>
            </tooltip-help-icon>
          </v-card-title>

          <v-form ref="form" class="interval-selector">
            <v-text-field
              :value="interval"
              class="interval align-center"
              type="number"
              hide-details
              dense
              solo
              @input="setInterval"
            >
              <template v-slot:prepend>
                Last
              </template>

              <template v-slot:append-outer>
                <v-select
                  :value="resolution"
                  class="resolution"
                  :items="resolutions"
                  label="Resolution"
                  hide-details
                  dense
                  solo
                  @input="setResolution"
                />
              </template>
            </v-text-field>

            <div v-if="intervalError" class="red--text">
              {{ intervalError }}
            </div>
          </v-form>
          <outstanding-reports-chart
            :bus="bus"
            :get-statistics-filters="getStatisticsFilters"
            :interval="interval"
            :resolution="resolution"
            :styles="{
              height: '400px',
              position: 'relative'
            }"
          />
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <component-severity-statistics
          :bus="bus"
          :namespace="namespace"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import _ from "lodash";
import { ccService, handleThriftError } from "@cc-api";
import { DateMixin } from "@/mixins";
import { BaseStatistics } from "@/components/Statistics";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

import Reports from "./Reports";
import { ComponentSeverityStatistics } from "./ComponentSeverityStatistics";
import FailedFilesDialog from "./FailedFilesDialog";
import OutstandingReportsChart from "./OutstandingReportsChart";
import SingleLineWidget from "./SingleLineWidget";

export default {
  name: "Overview",
  components: {
    ComponentSeverityStatistics,
    FailedFilesDialog,
    OutstandingReportsChart,
    Reports,
    SingleLineWidget,
    TooltipHelpIcon
  },
  mixins: [ BaseStatistics, DateMixin ],
  data() {
    const defaultInterval = "7";

    const resolutions = [ "days", "weeks", "months", "years" ];
    const defaultResolution = resolutions[0];


    let interval = this.$route.query["interval"];
    if (this.validateIntervalValue(interval)) {
      interval = defaultInterval;
    }

    let resolution = this.$route.query["resolution"];
    if (!resolution || !resolutions.includes(resolution)) {
      resolution = defaultResolution;
    }

    return {
      intervalError: null,
      interval,
      resolutions,
      resolution
    };
  },
  methods: {
    validateIntervalValue(val) {
      if (!val || isNaN(parseInt(val))) {
        return "Number is required!";
      }

      if (parseInt(val) > 31) {
        return "Interval value should between 1-31!";
      }

      return null;
    },

    setInterval: _.debounce(function (val) {
      this.intervalError = this.validateIntervalValue(val);
      if (this.intervalError) return;

      this.interval = val;
      this.updateUrl();

      this.intervalError = null;
    }, 300),

    setResolution(val) {
      this.resolution = val;
      this.updateUrl();
    },

    updateUrl() {
      const queryParams = Object.assign({}, this.$route.query, {
        interval: this.interval,
        resolution: this.resolution
      });

      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    getNumberOfReports(runIds, reportFilter, cmpData) {
      return new Promise(resolve => {
        ccService.getClient().getRunResultCount(runIds, reportFilter, cmpData,
          handleThriftError(res => {
            resolve(res.toNumber());
          }));
      });
    },

    getNumberOfFailedFiles() {
      return new Promise(resolve => {
        ccService.getClient().getFailedFilesCount(this.runIds,
          handleThriftError(res => {
            resolve(res);
          }));
      });
    },

    getNumberOfActiveCheckers() {
      const { runIds, reportFilter, cmpData } = this.getStatisticsFilters();
      const limit = null;
      const offset = 0;

      return new Promise(resolve => {
        ccService.getClient().getCheckerCounts(runIds, reportFilter, cmpData,
          limit, offset, handleThriftError(res => {
            resolve(res.length);
          }));
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.link {
  text-decoration: none;
  color: inherit;

  &:hover {
    color: var(--v-primary-lighten1);
  }
}

.num-of-failed-files {
  cursor: pointer;
}

.interval-selector {
  position: absolute;
  right: 50px;
  top: 0px;
  z-index: 100;

  .interval {
    width: 250px;
    border: 1px dashed grey;
    padding: 6px;
  }
  .resolution {
    width: 120px;
  }
}
</style>