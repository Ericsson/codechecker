<template>
  <v-container
    class="pa-0"
    fluid
  >
    <v-row>
      <v-col
        v-for="reportType in reportTypes"
        :key="reportType.label"
        class="pa-2"
        md="12"
        lg="6"
      >
        <v-card
          :color="reportType.color"
          class="pa-2"
        >
          <v-card-title
            class="text-h5"
          >
            <v-icon
              class="mr-2"
            >
              {{ reportType.icon }}
            </v-icon>
            {{ reportType.label }}

            <tooltip-help-icon
              color="white"
            >
              <div
                v-if="reportType.id === 'new'"
                class="mb-2"
              >
                <p
                  class="mb-2"
                >
                  Shows the number of new outstanding reports since the last
                  <i>x</i> days. Clicking on each item will display
                  the corresponding reports in a list.
                </p>
                <p
                  class="mb-2"
                >
                  Closed reports: No longer detected by the analyzer or
                  identified as <b>false positive</b> or <b>intentional</b>
                  findings.
                </p>
                <p>
                  <b>Note: Clicking on any item will reset the filters to
                    reflect the displayed figures.</b>
                </p>
              </div>
              <div
                v-else
                class="mb-2"
              >
                <p
                  class="mb-2"
                >
                  Shows the number of reports which were closed in the last
                  <i>x</i> days. Clicking on each item will display the
                  corresponding reports in a list.
                </p>
                <p
                  class="mb-2"
                >
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
                      'open-reports-date':
                        dateUtils.dateTimeToStr(columnData.date[0]),
                      'compared-to-open-reports-date':
                        dateUtils.dateTimeToStr(columnData.date[1]),
                    } : {
                      'fixed-after':
                        dateUtils.dateTimeToStr(columnData.date[0]),
                      'fixed-before':
                        dateUtils.dateTimeToStr(columnData.date[1])
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
                  <div
                    class="text-h3 text-white"
                  >
                    {{ columnData.value }}
                  </div>
                  <v-card-title
                    class="justify-center text-white"
                  >
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

<script setup>
import {
  endOfToday,
  startOfToday,
  startOfYesterday,
  subDays
} from "date-fns";
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useDateUtils } from "@/composables/useDateUtils";
import { ccService, handleThriftError } from "@cc-api";
import {
  CompareData,
  DateInterval,
  DiffType,
  ReportDate,
  ReportFilter
} from "@cc/report-server-types";

import TooltipHelpIcon from "@/components/TooltipHelpIcon.vue";

const props = defineProps({
  bus: { type: Object, required: true },
  runIds: {
    required: true,
    validator: _v => typeof _v === "object" || _v === null
  },
  reportFilter: { type: Object, required: true },
});

const router = useRouter();
const dateUtils = useDateUtils();

const last7Days = subDays(endOfToday(), 7);
const last31Days = subDays(endOfToday(), 31);
const runName = router.currentRoute.value.query["run"];

const cols = [
  { label: "Today",  date: [ startOfToday(), endOfToday() ] },
  { label: "Yesterday", date: [ startOfYesterday(), endOfToday() ] },
  { label: "Last 7 days", date: [ last7Days, endOfToday() ] },
  { label: "Last 31 days", date: [ last31Days, endOfToday() ] }
];

const reportTypes = ref([
  {
    id: "new",
    label: "Number of new outstanding reports since",
    color: "red",
    icon: "mdi-arrow-up",
    getValue: getNewReports,
    cols: cols.map(_c => ({ ..._c, value: null, loading: null }))
  },
  {
    id: "resolved",
    label: "Number of resolved reports since",
    color: "green",
    icon: "mdi-arrow-down",
    getValue: getResolvedReports,
    cols: cols.map(_c => ({ ..._c, value: null, loading: null }))
  },
]);

function fetchValues() {
  reportTypes.value.forEach(_type =>
    _type.cols.forEach(_column =>  _type.getValue(_column, _column.date)));
}

function getReportCount(column, runIds, reportFilter, cmpData) {
  column.loading = "white";

  ccService.getClient().getRunResultCount(runIds, reportFilter, cmpData,
    handleThriftError(_res => {
      column.value = _res.toNumber();
      column.loading = null;
    }));
}

function getNewReports(column, date) {
  const _rFilter = new ReportFilter(props.reportFilter);
  _rFilter.detectionStatus = null;
  _rFilter.reviewStatus = null;
  _rFilter.openReportsDate = dateUtils.getUnixTime(date[0]);

  const _cmpData = new CompareData({
    runIds: props.runIds,
    openReportsDate: dateUtils.getUnixTime(date[1]),
    diffType: DiffType.NEW
  });

  getReportCount(column, props.runIds, _rFilter, _cmpData);
}

function getResolvedReports(column, date) {
  const _rFilter = new ReportFilter(props.reportFilter);
  _rFilter.reviewStatus = null;
  _rFilter.detectionStatus = null;
  _rFilter.date = new ReportDate({
    fixed: new DateInterval({
      after: dateUtils.getUnixTime(date[0]),
      before: dateUtils.getUnixTime(date[1])
    })
  });

  const _cmpData = null;
  getReportCount(column, props.runIds, _rFilter, _cmpData);
}

defineExpose({ fetchValues });
</script>

<style lang="scss" scoped>
.v-card__title {
  word-break: break-word;
}

.day-col:hover {
  opacity: 0.8;
}
</style>
