<template>
  <v-container fluid>
    <reports
      :bus="bus"
      :get-statistics-filters="getStatisticsFilters"
    />

    <v-row>
      <v-col>
        <single-line-widget
          icon="mdi-bell-ring"
          color="red"
          label="Outstanding reports"
          help-message="Number of reports which are not fixed yet."
          :bus="bus"
          :get-value="getNumberOfOutstandingReports"
        >
          <template #value="{ value }">
            <router-link
              :to="{
                name: 'reports',
                query: {
                  ...$router.currentRoute.query,
                  ...{
                    'open-reports-date': dateTimeToStr(new Date),
                  }
                }
              }"
              class="link"
              color="inherit"
            >
              {{ value }}
            </router-link>
          </template>
        </single-line-widget>
      </v-col>

      <v-col>
        <single-line-widget
          icon="mdi-close"
          color="red"
          label="Number of failed files"
          help-message="Number of failed files in the current product."
          :bus="bus"
          :get-value="getNumberOfFailedFiles"
        >
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
          help-message="Number of checkers which found some report in the
            current product."
          :bus="bus"
          :get-value="getNumberOfActiveCheckers"
        />
      </v-col>
    </v-row>

    <v-row class="my-4">
      <v-col>
        <v-card flat>
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
import { ReportFilter } from "@cc/report-server-types";
import { DateMixin } from "@/mixins";
import { BaseStatistics } from "@/components/Statistics";
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
    SingleLineWidget
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

    getNumberOfOutstandingReports() {
      const { runIds, reportFilter, cmpData } = this.getStatisticsFilters();

      const repFilter = new ReportFilter(reportFilter);
      repFilter.openReportsDate = this.getUnixTime(new Date);

      return this.getNumberOfReports(runIds, repFilter, cmpData);
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
  z-index: 1000;

  .last-month {
    width: 180px;
    border: 1px dashed grey;
    padding: 6px;
  }
}
</style>