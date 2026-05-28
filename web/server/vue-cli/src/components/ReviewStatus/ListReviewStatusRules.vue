<template>
  <v-data-table
    v-model:options="pagination"
    :headers="headers"
    :items="rules"
    :items-length="totalItems"
    :loading="loading"
    :mobile-breakpoint="1000"
    loading-text="Loading review status rules..."
    :footer-props="footerProps"
    item-key="reportHash"
  >
    <template v-slot:top>
      <edit-review-status-rule-dialog
        v-model="editDialog"
        :rule="selected"
        @on:confirm="fetchReviewStatusRules"
      />

      <remove-review-status-rule-dialog
        v-model="removeDialog"
        :rule="selected"
        @on:confirm="fetchReviewStatusRules"
      />

      <remove-filtered-rules-dialog
        v-model="removeFilteredRuleDialog"
        :total="totalItems"
        :filter="filter"
        @on:confirm="fetchReviewStatusRules"
      />

      <v-toolbar
        elevation="0"
        color="transparent"
        class="mb-4"
      >
        <v-container class="pa-0" fluid>
          <v-row align="center">
            <v-col class="pa-0">
              <review-status-rule-filter
                class="review-status-rule-filters"
                :bus="bus"
                @on:filter="filterReviewStatusRules"
              />
            </v-col>
            <v-col class="pa-0" align="right" cols="auto">
              <v-btn
                color="error"
                class="remove-filtered-rules-btn mr-2"
                variant="outlined"
                :disabled="loading"
                @click="removeFilteredRuleDialog = true"
              >
                Remove filtered rules
              </v-btn>

              <v-btn
                color="primary"
                class="clear-all-filters-btn mr-2"
                variant="outlined"
                @click="clearAllFilters"
              >
                Clear all filters
              </v-btn>

              <v-btn
                color="primary"
                class="new-rule-btn mr-2"
                variant="outlined"
                @click="newReviewStatusRule"
              >
                New
              </v-btn>

              <v-btn
                icon
                title="Reload review status rules"
                color="primary"
                @click="fetchReviewStatusRules"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </v-container>
      </v-toolbar>
    </template>

    <template #item.status="{ item }">
      <review-status-label
        :value="item.status"
        label="TODO"
      />
    </template>

    <template #item.reportHash="{ item }">
      <router-link
        class="report-hash"
        :title="item.reportHash"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.value.query,
          'report-hash': item.reportHash,
          'review-status': reviewStatusFromCodeToString(item.status)
        }}"
      >
        {{ truncate(item.reportHash, 10) }}
      </router-link>
    </template>

    <template #item.date="{ item }">
      <v-chip
        class="ma-2"
        color="primary"
        variant="outlined"
      >
        <v-icon
          start
        >
          mdi-calendar-range
        </v-icon>
        {{ prettifiedDate(item.date) }}
      </v-chip>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="remove-btn mr-2"
        icon="mdi-trash-can-outline"
        color="error"
        size="small"
        variant="tonal"
        :disabled="loading"
        @click="removeReviewStatusRule(item)"
      />

      <v-btn
        class="edit-btn"
        icon="mdi-pencil"
        color="primary"
        size="small"
        variant="tonal"
        :disabled="loading"
        @click="editReviewStatusRule(item)"
      />
    </template>
  </v-data-table>
</template>

<script setup>
import mitt from "mitt";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ccService, handleThriftError } from "@cc-api";
import {
  Order,
  ReviewStatusRuleSortMode,
  ReviewStatusRuleSortType
} from "@cc/report-server-types";

import { useReviewStatus } from "@/composables/useReviewStatus";
import { useDateUtils } from "@/composables/useDateUtils";
import EditReviewStatusRuleDialog from "./EditReviewStatusRuleDialog";
import RemoveFilteredRulesDialog from "./RemoveFilteredRulesDialog";
import RemoveReviewStatusRuleDialog from "./RemoveReviewStatusRuleDialog";
import ReviewStatusLabel from "./ReviewStatusLabel";
import ReviewStatusRuleFilter from "./ReviewStatusRuleFilter";

const route = useRoute();
const router = useRouter();

const { prettifyDate } = useDateUtils();

const reviewStatus = useReviewStatus();

const itemsPerPageOptions = [
  { value: 25, title: "25" },
  { value: 50, title: "50" },
  { value: 100, title: "100" },
  { value: -1, title: "$vuetify.dataFooter.itemsPerPageAll" }
];

const page = ref(parseInt(route.query["page"]) || 1);
const itemsPerPage = ref(
  parseInt(route.query["items-per-page"]) ||
  itemsPerPageOptions[0].value
);

const sortBy = ref(
  route.query["sort-by"] 
    ? [ { 
      key: route.query["sort-by"], 
      order: route.query["sort-desc"] === "true" ? "desc" : "asc" 
    } ]
    : [ { key: "name", order: "asc" } ]
);

const initialized = ref(false);

const footerProps = {
  itemsPerPageOptions: itemsPerPageOptions
};
const totalItems = ref(0);
const rules = ref([]);
const filter = ref(null);
const loading = ref(false);
const selected = ref(null);
const editDialog = ref(false);
const removeDialog = ref(false);
const removeFilteredRuleDialog = ref(false);
const bus = mitt();

const headers = [
  {
    title: "Report hash",
    key: "reportHash",
    sortable: true
  },
  {
    title: "Review status",
    key: "status",
    sortable: true
  },
  {
    title: "Message",
    key: "message",
    sortable: false
  },
  {
    title: "Author",
    key: "author",
    sortable: true
  },
  {
    title: "Date",
    key: "date",
    sortable: true
  },
  {
    title: "Number of associated reports",
    key: "associatedReportCount",
    sortable: true,
    align: "center"
  },
  {
    title: "Actions",
    key: "actions",
    sortable: false
  },
];

const prettifiedDate = computed(function() {
  return function(date) {
    return prettifyDate(date);
  };
});

const reviewStatusFromCodeToString = computed(function() {
  return reviewStatus.reviewStatusFromCodeToString;
});

watch(
  [ page, itemsPerPage, sortBy ],
  () => {
    updateUrl();
    if (initialized.value) {
      fetchReviewStatusRules();
    }
  }, { deep: true }
);

function updateUrl() {
  const _defaultItemsPerPage = itemsPerPageOptions[0].value;
  const _itemsPerPage =
    itemsPerPage.value === _defaultItemsPerPage
      ? undefined
      : itemsPerPage;

  const _page = page.value === 1 ? undefined : page.value;
  const _sortBy = sortBy.value?.[0]?.key;
  const _sortDesc = sortBy.value?.[0]?.order === "desc";
  router.replace({
    query: {
      ...route.query,
      "items-per-page": _itemsPerPage,
      "page": _page,
      "sort-by": _sortBy,
      "sort-desc": _sortDesc,
    }
  }).catch(() => {});
}

function getSortMode() {
  let _type = null;
  const _sortBy = sortBy.value?.[0]?.key;

  switch (_sortBy) {
  case "reportHash":
    _type = ReviewStatusRuleSortType.REPORT_HASH;
    break;
  case "status":
    _type = ReviewStatusRuleSortType.STATUS;
    break;
  case "author":
    _type = ReviewStatusRuleSortType.AUTHOR;
    break;
  case "associatedReportCount":
    _type = ReviewStatusRuleSortType.ASSOCIATED_REPORTS_COUNT;
    break;
  default:
    _type = ReviewStatusRuleSortType.DATE;
  }

  const _ord = sortBy.value?.[0]?.order === "asc" ? Order.ASC : Order.DESC;

  return new ReviewStatusRuleSortMode({ type: _type, ord: _ord });
}

function filterReviewStatusRules(_filter) {
  filter.value = _filter;
  fetchReviewStatusRules();
}

function fetchReviewStatusRules() {
  loading.value = true;

  ccService.getClient().getReviewStatusRulesCount(
    filter.value,
    handleThriftError(_totalItems => {
      totalItems.value = _totalItems.toNumber();
    }));

  const _sortMode = getSortMode();
  const _limit = itemsPerPage.value;
  const _offset = _limit * (page.value - 1);

  return new Promise(resolve => {
    ccService.getClient().getReviewStatusRules(
      filter.value,
      _sortMode,
      _limit,
      _offset,
      handleThriftError(_rules => {
        rules.value = _rules.map(r => ({
          reportHash: r.reportHash,
          status: r.reviewData.status,
          message: r.reviewData.comment,
          author: r.reviewData.author,
          date: r.reviewData.date,
          associatedReportCount: r.associatedReportCount.toNumber()
        }));
        loading.value = false;
        initialized.value = true;

        resolve(rules.value);
      }));
  });
}

function clearAllFilters() {
  bus.emit("clear");
}

function editReviewStatusRule(rule) {
  selected.value = rule;
  editDialog.value = true;
}

function newReviewStatusRule() {
  selected.value = null;
  editDialog.value = true;
}

function removeReviewStatusRule(rule) {
  selected.value = rule;
  removeDialog.value = true;
}

function truncate(text, length) {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + "...";
}
</script>

<style lang="scss">
.report-hash {
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

:deep(.v-toolbar__content) {
  padding: 0;
}
</style>
