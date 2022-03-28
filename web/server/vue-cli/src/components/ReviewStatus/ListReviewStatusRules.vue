<template>
  <v-data-table
    :headers="headers"
    :items="rules"
    :loading="loading"
    :mobile-breakpoint="1000"
    :options.sync="pagination"
    loading-text="Loading review status rules..."
    :server-items-length.sync="totalItems"
    :footer-props="footerProps"
    item-key="reportHash"
  >
    <template v-slot:top>
      <edit-review-status-rule-dialog
        :value.sync="editDialog"
        :rule="selected"
        @on:confirm="fetchReviewStatusRules"
      />

      <remove-review-status-rule-dialog
        :value.sync="removeDialog"
        :rule="selected"
        @on:confirm="fetchReviewStatusRules"
      />

      <remove-filtered-rules-dialog
        :value.sync="removeFilteredRuleDialog"
        :total="totalItems"
        :filter="filter"
        @on:confirm="fetchReviewStatusRules"
      />

      <v-toolbar flat class="mb-4">
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
                outlined
                :disabled="loading"
                @click="removeFilteredRuleDialog = true"
              >
                Remove filtered rules
              </v-btn>

              <v-btn
                color="primary"
                class="clear-all-filters-btn mr-2"
                outlined
                @click="clearAllFilters"
              >
                Clear all filters
              </v-btn>

              <v-btn
                color="primary"
                class="new-rule-btn mr-2"
                outlined
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
      <review-status-label :value="item.status" label="TODO" />
    </template>

    <template #item.reportHash="{ item }">
      <router-link
        class="report-hash"
        :title="item.reportHash"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'report-hash': item.reportHash,
          'review-status': reviewStatusFromCodeToString(item.status)
        }}"
      >
        {{ item.reportHash | truncate(10) }}
      </router-link>
    </template>

    <template #item.date="{ item }">
      <v-chip
        class="ma-2"
        color="primary"
        outlined
      >
        <v-icon left>
          mdi-calendar-range
        </v-icon>
        {{ item.date | prettifyDate }}
      </v-chip>
    </template>

    <template v-slot:item.actions="{ item }">
      <v-btn
        class="remove-btn"
        icon
        color="error"
        :disabled="loading"
        @click="removeReviewStatusRule(item)"
      >
        <v-icon>mdi-trash-can-outline</v-icon>
      </v-btn>

      <v-btn
        class="edit-btn"
        icon
        color="primary"
        :disabled="loading"
        @click="editReviewStatusRule(item)"
      >
        <v-icon>mdi-pencil</v-icon>
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import Vue from "vue";

import { ccService, handleThriftError } from "@cc-api";
import {
  Order,
  ReviewStatusRuleSortMode,
  ReviewStatusRuleSortType
} from "@cc/report-server-types";

import { ReviewStatusMixin } from "@/mixins";
import EditReviewStatusRuleDialog from "./EditReviewStatusRuleDialog";
import RemoveReviewStatusRuleDialog from "./RemoveReviewStatusRuleDialog";
import RemoveFilteredRulesDialog from "./RemoveFilteredRulesDialog";
import ReviewStatusLabel from "./ReviewStatusLabel";
import ReviewStatusRuleFilter from "./ReviewStatusRuleFilter";

export default {
  name: "ListSourceComponents",
  components: {
    EditReviewStatusRuleDialog,
    RemoveFilteredRulesDialog,
    RemoveReviewStatusRuleDialog,
    ReviewStatusLabel,
    ReviewStatusRuleFilter
  },
  mixins: [ ReviewStatusMixin ],
  data() {
    const itemsPerPageOptions = [ 25, 50, 100 ];

    const page = parseInt(this.$router.currentRoute.query["page"]) || 1;
    const itemsPerPage =
      parseInt(this.$router.currentRoute.query["items-per-page"]) ||
      itemsPerPageOptions[0];
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    return {
      initialized: false,
      pagination: {
        page: page,
        itemsPerPage: itemsPerPage,
        sortBy: sortBy ? [ sortBy ] : [],
        sortDesc: sortDesc !== undefined ? [ sortDesc === "true" ] : []
      },
      footerProps: {
        itemsPerPageOptions: itemsPerPageOptions
      },
      totalItems: 0,
      rules: [],
      filter: null,
      loading: false,
      selected: null,
      editDialog: false,
      removeDialog: false,
      removeFilteredRuleDialog: false,
      bus: new Vue(),
      headers: [
        {
          text: "Report hash",
          value: "reportHash",
          sortable: true
        },
        {
          text: "Review status",
          value: "status",
          sortable: true
        },
        {
          text: "Message",
          value: "message",
          sortable: false
        },
        {
          text: "Author",
          value: "author",
          sortable: true
        },
        {
          text: "Date",
          value: "date",
          sortable: true
        },
        {
          text: "Number of associated reports",
          value: "associatedReportCount",
          sortable: true,
          align: "center"
        },
        {
          text: "Actions",
          value: "actions",
          sortable: false
        },
      ]
    };
  },

  watch: {
    pagination: {
      handler() {
        if (!this.initialized) return;

        const defaultItemsPerPage = this.footerProps.itemsPerPageOptions[0];
        const itemsPerPage =
          this.pagination.itemsPerPage === defaultItemsPerPage
            ? undefined
            : this.pagination.itemsPerPage;

        const page = this.pagination.page === 1
          ? undefined : this.pagination.page;
        const sortBy = this.pagination.sortBy.length
          ? this.pagination.sortBy[0] : undefined;
        const sortDesc = this.pagination.sortDesc.length
          ? this.pagination.sortDesc[0] : undefined;

        this.updateUrl({
          "items-per-page": itemsPerPage,
          "page": page,
          "sort-by": sortBy,
          "sort-desc": sortDesc,
        });

        this.fetchReviewStatusRules();
      },
      deep: true
    }
  },

  methods: {
    updateUrl(params) {
      this.$router.replace({
        query: {
          ...this.$route.query,
          ...params
        }
      }).catch(() => {});
    },

    getSortMode() {
      let type = null;
      switch (this.pagination.sortBy[0]) {
      case "reportHash":
        type = ReviewStatusRuleSortType.REPORT_HASH;
        break;
      case "status":
        type = ReviewStatusRuleSortType.STATUS;
        break;
      case "author":
        type = ReviewStatusRuleSortType.AUTHOR;
        break;
      case "associatedReportCount":
        type = ReviewStatusRuleSortType.ASSOCIATED_REPORTS_COUNT;
        break;
      default:
        type = ReviewStatusRuleSortType.DATE;
      }

      const ord = this.pagination.sortDesc[0] === false
        ? Order.ASC : Order.DESC;

      return new ReviewStatusRuleSortMode({ type: type, ord: ord });
    },

    filterReviewStatusRules(filter) {
      this.filter = filter;
      this.fetchReviewStatusRules();
    },

    fetchReviewStatusRules() {
      this.loading = true;

      // Get total item count.
      ccService.getClient().getReviewStatusRulesCount(this.filter,
        handleThriftError(totalItems => {
          this.totalItems = totalItems.toNumber();
        }));

      const sortMode = this.getSortMode();
      const limit = this.pagination.itemsPerPage;
      const offset = limit * (this.pagination.page - 1);

      return new Promise(resolve => {
        ccService.getClient().getReviewStatusRules(this.filter, sortMode,
          limit, offset, handleThriftError(rules => {
            this.rules = rules.map(r => ({
              reportHash: r.reportHash,
              status: r.reviewData.status,
              message: r.reviewData.comment,
              author: r.reviewData.author,
              date: r.reviewData.date,
              associatedReportCount: r.associatedReportCount.toNumber()
            }));
            this.loading = false;
            this.initialized = true;

            resolve(this.rules);
          }));
      });
    },

    clearAllFilters() {
      this.bus.$emit("clear");
    },

    editReviewStatusRule(rule) {
      this.selected = rule;
      this.editDialog = true;
    },

    newReviewStatusRule() {
      this.selected = null;
      this.editDialog = true;
    },

    removeReviewStatusRule(rule) {
      this.selected = rule;
      this.removeDialog = true;
    }
  }
};
</script>

<style lang="scss" scoped>
.report-hash {
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

::v-deep .v-toolbar__content {
  padding: 0;
}
</style>
