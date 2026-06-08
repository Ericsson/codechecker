<template>
  <v-container fluid>
    <v-row align="center">
      <v-col class="py-0">
        <v-text-field
          v-model="reportHash"
          class="report-hash"
          prepend-inner-icon="mdi-magnify"
          label="Search by report hash..."
          single-line
          hide-details
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="onTextFilterChanged"
        />
      </v-col>
      <v-col class="py-0">
        <select-review-status
          v-model="reviewStatusValue"
          label="Search by review status"
          @update:model-value="onFilterChanged"
        />
      </v-col>
      <v-col class="py-0">
        <v-text-field
          v-model="author"
          class="author"
          prepend-inner-icon="mdi-magnify"
          label="Search by author..."
          single-line
          hide-details
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="onTextFilterChanged"
        />
      </v-col>
      <v-col class="py-0">
        <v-checkbox
          v-model="noAssociatedReports"
          class="no-associated-reports ma-0 py-0"
          :hide-details="true"
          @change="onFilterChanged"
        >
          <template v-slot:label>
            No associated reports
            <tooltip-help-icon>
              Show only review status rules which have no associated reports
              and can be safely removed from the database without changing the
              statistics.
            </tooltip-help-icon>
          </template>
        </v-checkbox>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import _ from "lodash";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ReviewStatusRuleFilter } from "@cc/report-server-types";

import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { useReviewStatus } from "@/composables/useReviewStatus";
import SelectReviewStatus from "./SelectReviewStatus";

const props = defineProps({
  bus: { type: Object, required: true }
});

const emit = defineEmits([ "on:filter" ]);

const route = useRoute();
const router = useRouter();
const reviewStatus = useReviewStatus();

const queries = route.query;
const reportHash = ref(queries["report-hash"]);
const noAssociatedReports = ref(
  (queries["no-associated-reports"] && true) || false
);
const reviewStatusValue = ref(
  queries["review-status"]
    ? reviewStatus.reviewStatusFromStringToCode(queries["review-status"])
    : null
);
const author = ref(queries["author"]);

const status = computed(function() {
  if (reviewStatusValue.value !== null) {
    return reviewStatus.reviewStatusFromCodeToString(reviewStatusValue.value);
  }
  return null;
});

const filter = computed(function() {
  if (
    !reportHash.value &&
    !noAssociatedReports.value &&
    reviewStatusValue.value === null &&
    !author.value
  ) return;

  const _filter = new ReviewStatusRuleFilter();
  _filter.reportHashes = reportHash.value ? [ `${reportHash.value}*` ] : null;
  _filter.authors = author.value ? [ `${author.value}*` ] : null;
  _filter.reviewStatuses =
    reviewStatusValue.value !== null ? [ reviewStatusValue.value ] : null;
  _filter.noAssociatedReports = noAssociatedReports.value;

  return _filter;
});

onMounted(function() {
  onFilterChanged();

  props.bus.on("clear", () => {
    reportHash.value = null;
    author.value = null;
    reviewStatusValue.value = null;
    noAssociatedReports.value = null;

    onFilterChanged();
  });
});

onUnmounted(() => {
  props.bus.off("clear");
});

const onTextFilterChanged = _.debounce(function () {
  onFilterChanged();
}, 400);

function onFilterChanged () {
  emit("on:filter", filter.value);
  updateUrl({
    "report-hash": reportHash.value ? reportHash.value : undefined,
    "author": author.value ? author.value : undefined,
    "no-associated-reports": noAssociatedReports.value ? "on" : undefined,
    "review-status": status.value !== null ? status.value : undefined
  });
}

function updateUrl(params) {
  router.replace({
    query: {
      ...route.query,
      ...params
    }
  }).catch(() => {});
}
</script>
