<template>
  <v-container
    fluid
  >
    <reports
      ref="reportsRef"
      :bus="bus"
      :run-ids="baseStats.runIds.value"
      :report-filter="baseStats.reportFilter.value"
    />
    <v-row class="mt-4">
      <v-col
        class="px-2"
      >
        <single-line-widget
          icon="mdi-close"
          color="red"
          label="Number of failed files"
          :bus="bus"
          :value="failedFiles"
        >
          <template #help>
            Number of failed files in the current product.<br><br>
            Only the Run filter will affect this value.
          </template>

          <template #value="{ value }">
            <failed-files-dialog>
              <template #default="{ props: bindProps }">
                <span
                  v-bind="bindProps"
                  class="num-of-failed-files"
                >
                  {{ value }}
                </span>
              </template>
            </failed-files-dialog>
          </template>
        </single-line-widget>
      </v-col>

      <v-col
        class="px-2"
      >
        <single-line-widget
          icon="mdi-card-account-details"
          color="grey"
          label="Number of checkers reporting faults"
          :bus="bus"
          :value="activeCheckers"
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
            Outstanding reports

            <tooltip-help-icon>
              Shows the number of reports which were active in the last
              <i>x</i> months/days.<br><br>

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
              :model-value="interval"
              class="interval align-center"
              type="number"
              hide-details
              density="compact"
              variant="solo"
              @update:model-value="setInterval"
            >
              <template v-slot:prepend>
                Last
              </template>

              <template v-slot:append>
                <v-select
                  :model-value="resolution"
                  class="resolution"
                  :items="resolutions"
                  hide-details
                  density="compact"
                  variant="solo"
                  @update:model-value="setResolution"
                />
              </template>
            </v-text-field>

            <div v-if="intervalError" class="text-red">
              {{ intervalError }}
            </div>
          </v-form>
          <outstanding-reports-chart
            :bus="bus"
            :get-statistics-filters="baseStats.getStatisticsFilters"
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
  </v-container>
</template>

<script setup>
import _ from "lodash";
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { ccService, handleThriftError } from "@cc-api";

import FailedFilesDialog from "./FailedFilesDialog";
import OutstandingReportsChart from "./OutstandingReportsChart";
import Reports from "./Reports";
import SingleLineWidget from "./SingleLineWidget";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const route = useRoute();
const router = useRouter();
const baseStats = useBaseStatistics(props, null);
const failedFiles = ref(null);
const activeCheckers = ref(null);

const defaultInterval = "7";
const resolutions = [ "days", "weeks", "months", "years" ];
const defaultResolution = resolutions[0];

const loading = ref(false);
const reportsRef = ref(null);

baseStats.setupRefreshListener(fetchValues);

let _interval = route.query["interval"];
if (validateIntervalValue(_interval)) {
  _interval = defaultInterval;
}

let _resolution = route.query["resolution"];
if (!_resolution || !resolutions.includes(_resolution)) {
  _resolution = defaultResolution;
}

const intervalError = ref(null);
const interval = ref(_interval);
const resolution = ref(_resolution);

async function fetchValues() {
  loading.value = true;
  failedFiles.value = await getNumberOfFailedFiles();
  activeCheckers.value = await getNumberOfActiveCheckers();
  reportsRef.value?.fetchValues();
  loading.value = false;
}

function validateIntervalValue(val) {
  if (!val || isNaN(parseInt(val))) {
    return "Number is required!";
  }

  if (parseInt(val) > 31) {
    return "Interval value should between 1-31!";
  }

  return null;
}

const setInterval = _.debounce(function(_val) {
  intervalError.value = validateIntervalValue(_val);
  if (intervalError.value) return;

  interval.value = _val;
  updateUrl();

  intervalError.value = null;
}, 300);

function setResolution(_val) {
  resolution.value = _val;
  updateUrl();
}

function updateUrl() {
  const _queryParams = Object.assign({}, route.query, {
    interval: interval.value,
    resolution: resolution.value
  });

  router.replace({ query: _queryParams }).catch(() => {});
}

function getNumberOfFailedFiles() {
  return new Promise(_resolve => {
    ccService.getClient().getFailedFilesCount(
      baseStats.runIds.value,
      handleThriftError(_res => {
        _resolve(_res);
      }));
  });
}

function getNumberOfActiveCheckers() {
  const {
    runIds: _runIds,
    reportFilter: _reportFilter,
    cmpData: _cmpData
  } = baseStats.getStatisticsFilters();
  const _limit = null;
  const _offset = 0;

  return new Promise(_resolve => {
    ccService.getClient().getCheckerCounts(_runIds, _reportFilter, _cmpData,
      _limit, _offset, handleThriftError(_res => {
        _resolve(_res.length);
      }));
  });
}
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
    padding: 6px;
  }
  .resolution {
    width: 120px;
  }
}
</style>