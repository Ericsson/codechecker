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
              <div v-if="reportType.id === 'new'">
                Shows the number of reports which were active in the last
                <i>x</i> days.<br><br>

                Reports marked as <b>False positive</b> or <b>Intentional</b>
                will be <i>excluded</i> from these numbers.<br><br>
              </div>
              <div v-else>
                Shows the number of reports which were solved in the last
                <i>x</i> days.<br><br>

                For now reports marked as <b>False positive</b> or
                <b>Intentional</b> are not considered to be resolved by these
                numbers. A report is marked as resolved only when it disspeared
                from a storage.<br><br>
              </div>

              <div>
                The following filters don't affect these values:
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
              v-for="c in reportType.cols"
              :key="c.label"
              :cols="12 / reportType.cols.length"
            >
              <router-link
                :to="{
                  name: 'reports',
                  query: {
                    ...$router.currentRoute.query,
                    ...{
                      'newcheck': undefined,
                      'compared-to-open-reports-date': undefined,
                    },
                    ...(reportType.id === 'new' ? {
                      'open-reports-date': dateTimeToStr(c.date[0]),
                      'compared-to-open-reports-date':
                        dateTimeToStr(c.date[1]),
                      'diff-type': 'New'
                    } : {
                      'fixed-after': dateTimeToStr(c.date[0]),
                      'fixed-before': dateTimeToStr(c.date[1])
                    })
                  }
                }"
                class="text-decoration-none"
              >
                <v-card
                  class="day-col text-center"
                  color="transparent"
                  :loading="c.loading"
                  flat
                >
                  <div class="text-h2">
                    {{ c.value }}
                  </div>
                  <v-card-title class="justify-center">
                    {{ c.label }}
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
  endOfYesterday,
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
    const now = endOfToday();
    const last7Days = subDays(now, 7);
    const last31Days = subDays(now, 31);

    const cols = [
      { label: "Today",  date: [ startOfToday(), now ] },
      { label: "Yesterday", date: [ startOfYesterday(), endOfYesterday() ] },
      { label: "Last 7 days", date: [ last7Days, now ] },
      { label: "Last 31 days", date: [ last31Days, now ] }
    ];

    return {
      reportTypes: [
        {
          id: "new",
          label: "Number of outstanding reports",
          color: "red",
          icon: "mdi-arrow-up",
          getValue: this.getNewReports,
          cols: cols.map(c => ({ ...c, value: null, loading: null }))
        },
        {
          id: "resolved",
          label: "Number of resolved reports",
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
    };
  },
  activated() {
    this.bus.$on("refresh", () => this.fetchValues());
  },
  methods: {
    fetchValues() {
      this.reportTypes.forEach(t =>
        t.cols.forEach(c =>  t.getValue(c, c.date)));
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
      rFilter.reviewStatus = this.activeReviewStatuses;
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
