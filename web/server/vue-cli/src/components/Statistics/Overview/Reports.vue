<template>
  <v-container class="pa-0" fluid>
    <v-row>
      <v-col
        v-for="reportType in reportTypes"
        :key="reportType.label"
        md="12"
        lg="6"
      >
        <v-card :color="reportType.color" dark>
          <v-card-title class="text-h4">
            <v-icon class="mr-2">
              {{ reportType.icon }}
            </v-icon>
            {{ reportType.label }}

            <tooltip-help-icon color="white">
              <div v-if="reportType.id === 'new'" class="mb-2">
                <p class="mb-2">
                  Shows the number of new outstanding reports since the last
                  <i>x</i> days. Clicking on each item will display
                  the corresponding reports in a list.
                </p>
                <p class="mb-2">
                  Closed reports: No longer detected by the analyzer or
                  identified as <b>false positive</b> or <b>intentional</b>
                  findings.
                </p>
                <p>
                  <b>Note: Clicking on any item will reset the filters to
                    reflect the displayed figures.</b>
                </p>
              </div>
              <div v-else class="mb-2">
                <p class="mb-2">
                  Shows the number of reports which were closed in the last
                  <i>x</i> days. Clicking on each item will display the
                  corresponding reports in a list.
                </p>
                <p class="mb-2">
                  Closed reports: No longer detected by the analyzer or
                  identified as <b>false positive</b> or <b>intentional</b>
                  findings.
                </p>
                <p>
                  <b>Note: Clicking on any item will reset the filters to
                    reflect the displayed figures.</b>
                </p>
              </div>
              <div>
                The following filters does not affect these values:
                <ul>
                  <li><b>Outstanding reports on a given date</b> filter.</li>
                  <li>All filters in the <b>COMPARE TO</b> section.</li>
                  <li><b>Latest Review Status</b> filter.</li>
                  <li><b>Latest Detection Status</b> filter.</li>
                </ul>
              </div>
            </tooltip-help-icon>
          </v-card-title>
          <v-row>
            <v-col
              v-for="columnData in reportType.cols"
              :key="columnData.label"
              :cols="12 / reportType.cols.length"
            >
              <router-link
                :to="{
                  name: 'reports',
                  query: {
                    ...{
                      'detection-status': undefined,
                      'run': runName,
                    },
                    ...(reportType.id === 'new' ? {
                      'diff-type': 'New',
                      'newcheck': runName,
                      'open-reports-date': dateTimeToStr(columnData.date[0]),
                      'compared-to-open-reports-date':
                        dateTimeToStr(columnData.date[1]),
                    } : {
                      'fixed-after': dateTimeToStr(columnData.date[0]),
                      'fixed-before': dateTimeToStr(columnData.date[1])
                    })
                  }
                }"
                class="text-decoration-none"
              >
                <v-card
                  class="day-col text-center"
                  color="transparent"
                  :loading="columnData.loading"
                  flat
                >
                  <div class="text-h2">
                    {{ columnData.value }}
                  </div>
                  <v-card-title class="justify-center">
                    {{ columnData.label }}
                  </v-card-title>
                </v-card>
              </router-link>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
  endOfToday,
  startOfToday,
  startOfYesterday,
  subDays
} from "date-fns";
import { ccService, handleThriftError } from "@cc-api";
import {
  CompareData,
  DateInterval,
  DiffType,
  ReportDate,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";
import { DateMixin } from "@/mixins";

import TooltipHelpIcon from "@/components/TooltipHelpIcon.vue";

export default {
  name: "Reports",
  components: { TooltipHelpIcon },
  mixins: [ DateMixin ],
  props: {
    bus: { type: Object, required: true },
    runIds: {
      required: true,
      validator: v => typeof v === "object" || v === null
    },
    reportFilter: { type: Object, required: true },
  },
  data() {
    const last7Days = subDays(endOfToday(), 7);
    const last31Days = subDays(endOfToday(), 31);
    const runName = this.$router.currentRoute.query["run"];

    const cols = [
      { label: "Today",  date: [ startOfToday(), endOfToday() ] },
      { label: "Yesterday", date: [ startOfYesterday(), endOfToday() ] },
      { label: "Last 7 days", date: [ last7Days, endOfToday() ] },
      { label: "Last 31 days", date: [ last31Days, endOfToday() ] }
    ];

    return {
      reportTypes: [
        {
          id: "new",
          label: "Number of new outstanding reports since",
          color: "red",
          icon: "mdi-arrow-up",
          getValue: this.getNewReports,
          cols: cols.map(c => ({ ...c, value: null, loading: null }))
        },
        {
          id: "resolved",
          label: "Number of resolved reports since",
          color: "green",
          icon: "mdi-arrow-down",
          getValue: this.getResolvedReports,
          cols: cols.map(c => ({ ...c, value: null, loading: null }))
        },
      ],
      activeReviewStatuses:
        [ ReviewStatus.UNREVIEWED, ReviewStatus.CONFIRMED ],
      resolvedReviewStatuses:
        [ ReviewStatus.FALSE_POSITIVE, ReviewStatus.INTENTIONAL ],
      runName,
    };
  },
  activated() {
    this.bus.$on("refresh", () => this.fetchValues());
  },
  methods: {
    fetchValues() {
      this.reportTypes.forEach(type =>
        type.cols.forEach(column =>  type.getValue(column, column.date)));
    },

    getReportCount(column, runIds, reportFilter, cmpData) {
      column.loading = "white";

      ccService.getClient().getRunResultCount(runIds, reportFilter, cmpData,
        handleThriftError(res => {
          column.value = res.toNumber();
          column.loading = null;
        }));
    },

    getNewReports(column, date) {
      const rFilter = new ReportFilter(this.reportFilter);
      rFilter.detectionStatus = null;
      rFilter.reviewStatus = this.activeReviewStatuses;
      rFilter.openReportsDate = this.getUnixTime(date[0]);

      const cmpData = new CompareData({
        runIds: this.runIds,
        openReportsDate: this.getUnixTime(date[1]),
        diffType: DiffType.NEW
      });

      this.getReportCount(column, this.runIds, rFilter, cmpData);
    },

    getResolvedReports(column, date) {
      const rFilter = new ReportFilter(this.reportFilter);
      rFilter.detectionStatus = null;
      rFilter.date = new ReportDate({
        fixed: new DateInterval({
          after: this.getUnixTime(date[0]),
          before: this.getUnixTime(date[1])
        })
      });

      const cmpData = null;
      this.getReportCount(column, this.runIds, rFilter, cmpData);
    },
  }
};
</script>

<style lang="scss" scoped>
.v-card__title {
  word-break: break-word;
}

.day-col:hover {
  opacity: 0.8;
}
</style>
