<template>
  <splitpanes class="default-theme">
    <pane size="20">
      <report-filter
        v-fill-height
        :namespace="namespace"
        :report-count="totalItems"
        @refresh="refresh"
      />
    </pane>
    <pane>
      <v-data-table
        v-fill-height
        :headers="tableHeaders"
        :items="formattedReports"
        :options.sync="pagination"
        :loading="loading"
        loading-text="Loading reports..."
        :server-items-length.sync="totalItems"
        :footer-props="footerProps"
        :must-sort="true"
        item-key="name"
      >
        <template #item.bugHash="{ item }">
          <span :title="item.bugHash">
            {{ item.bugHash | truncate(10) }}
          </span>
        </template>

        <template #item.checkedFile="{ item }">
          <router-link
            :to="{ name: 'report-detail', query: {
              ...$router.currentRoute.query,
              reportId: item.reportId ? item.reportId : undefined,
              reportHash: item.reportId ? undefined : item.bugHash
            }}"
          >
            {{ item.checkedFile }}
          </router-link>
        </template>

        <template #item.severity="{ item }">
          <severity-icon :status="item.severity" />
        </template>

        <template #item.bugPathLength="{ item }">
          <v-chip :color="getBugPathLenColor(item.bugPathLength)">
            {{ item.bugPathLength }}
          </v-chip>
        </template>

        <template #item.reviewData="{ item }">
          <review-status-icon :status="parseInt(item.reviewData.status)" />
        </template>

        <template #item.detectionStatus="{ item }">
          <detection-status-icon
            :status="parseInt(item.detectionStatus)"
            :title="item.$detectionStatusTitle"
          />
        </template>
      </v-data-table>
    </pane>
  </splitpanes>
</template>

<script>
import { Pane, Splitpanes } from "splitpanes";

import { mapGetters } from "vuex";

import { ccService, handleThriftError } from "@cc-api";
import { Order, SortMode, SortType } from "@cc/report-server-types";

import { FillHeight } from "@/directives";
import { BugPathLengthColorMixin, DetectionStatusMixin } from "@/mixins";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";

import { ReportFilter } from "@/components/Report/ReportFilter";

const namespace = "report";

export default {
  name: "Reports",
  components: {
    Splitpanes,
    Pane,
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon,
    ReportFilter
  },
  directives: { FillHeight },
  mixins: [ BugPathLengthColorMixin, DetectionStatusMixin ],

  data() {
    const itemsPerPageOptions = [ 25, 100, 250, 500 ];

    const page = parseInt(this.$router.currentRoute.query["page"]) || 1;
    const itemsPerPage =
      parseInt(this.$router.currentRoute.query["items-per-page"]) ||
      itemsPerPageOptions[0];
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    return {
      headers: [
        {
          text: "Report hash",
          value: "bugHash",
          sortable: false
        },
        {
          text: "File",
          value: "checkedFile",
          sortable: true
        },
        {
          text: "Message",
          value: "checkerMsg",
          sortable: false
        },
        {
          text: "Checker name",
          value: "checkerId",
          sortable: true
        },
        {
          text: "Severity",
          value: "severity",
          sortable: true
        },
        {
          text: "Bug path length",
          value: "bugPathLength",
          align: "center",
          sortable: true
        },
        {
          text: "Review status",
          value: "reviewData",
          align: "center",
          sortable: true
        },
        {
          text: "Detection status",
          value: "detectionStatus",
          align: "center",
          sortable: true
        }
      ],
      reports: [],
      namespace: namespace,
      pagination: {
        page: page,
        itemsPerPage: itemsPerPage,
        sortBy: sortBy ? [ sortBy ] : [],
        sortDesc: sortDesc !== undefined ? [ !!sortDesc ] : []
      },
      footerProps: {
        itemsPerPageOptions: itemsPerPageOptions
      },
      totalItems: 0,
      loading: false,
      runIdsUnwatch: null,
      reportFilterUnwatch: null,
      cmpDataUnwatch: null,
      initalized: false
    };
  },

  computed: {
    ...mapGetters(namespace, {
      runIds: "getRunIds",
      reportFilter: "getReportFilter",
      cmpData: "getCmpData"
    }),

    tableHeaders() {
      if (!this.headers) return;

      return this.headers.filter(header => {
        if (header.value === "detectionStatus") {
          return !this.reportFilter.isUnique;
        }

        return true;
      });
    },

    formattedReports() {
      return this.reports.map(report => {
        const detectionStatus =
          this.detectionStatusFromCodeToString(report.detectionStatus);
        const detectedAt = report.detectedAt
          ? this.$options.filters.prettifyDate(report.detectedAt) : null;
        const fixedAt = report.fixedAt
          ? this.$options.filters.prettifyDate(report.fixedAt) : null;

        const detectionStatusTitle = [
          `Status: ${detectionStatus}`,
          ...(detectedAt ? [ `Detected at: ${detectedAt}` ] : []),
          ...(fixedAt ? [ `Fixed at: ${fixedAt}` ] : [])
        ].join("\n");

        return {
          ...report,
          "$detectionStatusTitle": detectionStatusTitle
        };
      });
    },
  },

  watch: {
    pagination: {
      handler() {
        this.updateUrl();
        if (this.initalized) {
          this.fetchReports();
        }
      },
      deep: true
    },
  },

  methods: {
    getSortMode() {
      let type = null;
      switch (this.pagination.sortBy[0]) {
      case "checkedFile":
        type = SortType.FILENAME;
        break;
      case "checkerId":
        type = SortType.CHECKER_NAME;
        break;
      case "detectionStatus":
        type = SortType.DETECTION_STATUS;
        break;
      case "reviewData":
        type = SortType.REVIEW_STATUS;
        break;
      case "bugPathLength":
        type = SortType.BUG_PATH_LENGTH;
        break;
      default:
        type = SortType.SEVERITY;
      }

      const ord = this.pagination.sortDesc[0] ? Order.DESC : Order.ASC;

      return [ new SortMode({ type: type, ord: ord }) ];
    },

    updateUrl() {
      const defaultItemsPerPage = this.footerProps.itemsPerPageOptions[0];
      const itemsPerPage =
        this.pagination.itemsPerPage === defaultItemsPerPage
          ? undefined
          : this.pagination.itemsPerPage;

      const page = this.pagination.page === 1
        ? undefined : this.pagination.page;
      const sortBy = this.pagination.sortBy.length
        ? this.pagination.sortBy : undefined;
      const sortDesc = this.pagination.sortDesc.length
        ? this.pagination.sortDesc : undefined;

      this.$router.replace({
        query: {
          ...this.$route.query,
          "items-per-page": itemsPerPage,
          "page": page,
          "sort-by": sortBy,
          "sort-desc": sortDesc,
        }
      }).catch(() => {});
    },

    refresh() {
      ccService.getClient().getRunResultCount(this.runIds,
        this.reportFilter, this.cmpData, handleThriftError(res => {
          this.totalItems = res.toNumber();
        }));

      if (this.pagination.page !== 1 && this.initalized) {
        this.pagination.page = 1;
      } else {
        this.fetchReports();
      }
    },

    fetchReports() {
      this.loading = true;

      const limit = this.pagination.itemsPerPage;
      const offset = limit * (this.pagination.page - 1);
      const sortType = this.getSortMode();
      const getDetails = false;

      ccService.getClient().getRunResults(this.runIds, limit, offset, sortType,
        this.reportFilter, this.cmpData, getDetails,
        handleThriftError(reports => {
          this.reports = reports;
          this.loading = false;
          this.initalized = true;
        }));
    }
  }
};
</script>

<style lang="scss" scoped>
.splitpanes.default-theme {
  .splitpanes__pane {
    background-color: inherit;
  }
}
</style>
