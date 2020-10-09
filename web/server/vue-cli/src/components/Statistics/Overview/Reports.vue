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
          </v-card-title>
          <v-row>
            <v-col
              v-for="c in reportType.cols"
              :key="c.label"
              :cols="12 / reportType.cols.length"
            >
              <v-card
                class="text-center"
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
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
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
  ReportFilter
} from "@cc/report-server-types";
import { DateMixin } from "@/mixins";

export default {
  name: "Reports",
  mixins: [ DateMixin ],
  props: {
    bus: { type: Object, required: true },
    getStatisticsFilters: { type: Function, required: true }
  },
  data() {
    const now = new Date();
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
          label: "New reports",
          color: "red",
          icon: "mdi-arrow-up",
          getValue: this.getNewReports,
          cols: cols.map(c => ({ ...c, value: null, loading: null }))
        },
        {
          label: "Number of resolved reports",
          color: "green",
          icon: "mdi-arrow-down",
          getValue: this.getResolvedReports,
          cols: cols.map(c => ({ ...c, value: null, loading: null }))
        },
      ]
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
      const { runIds, reportFilter } = this.getStatisticsFilters();

      const rFilter = new ReportFilter(reportFilter);
      rFilter.openReportsDate = this.getUnixTime(date[0]);

      const cmpData = new CompareData({
        openReportsDate: this.getUnixTime(date[1]),
        diffType: DiffType.NEW
      });

      this.getReportCount(column, runIds, rFilter, cmpData);
    },

    getResolvedReports(column, date) {
      const cmpData = null;
      const { runIds, reportFilter } = this.getStatisticsFilters();

      const rFilter = new ReportFilter(reportFilter);
      rFilter.date = new ReportDate({
        fixed: new DateInterval({
          after: this.getUnixTime(date[0]),
          before: this.getUnixTime(date[1])
        })
      });

      this.getReportCount(column, runIds, rFilter, cmpData);
    },
  }
};
</script>

<style lang="scss" scoped>
.v-card__title {
  word-break: break-word;
}
</style>
