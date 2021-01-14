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

          <div class="last-month-selector">
            <v-text-field
              v-model="lastMonth"
              class="last-month align-center"
              type="number"
              hide-details
              dense
              solo
            >
              <template v-slot:prepend>
                Last
              </template>

              <template v-slot:append-outer>
                month(s).
              </template>
            </v-text-field>
          </div>
          <outstanding-reports-chart
            :bus="bus"
            :get-statistics-filters="getStatisticsFilters"
            :last-month="lastMonth"
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
    return {
      lastMonth: "6"
    };
  },
  methods: {
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

.last-month-selector {
  position: absolute;
  right: 50px;
  top: 0px;
  z-index: 100;

  .last-month {
    width: 180px;
    border: 1px dashed grey;
    padding: 6px;
  }
}
</style>