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
          outlined
          solo
          flat
          dense
          clearable
          @input="onTextFilterChanged"
        />
      </v-col>
      <v-col class="py-0">
        <select-review-status
          v-model="reviewStatus"
          label="Search by review status"
          @change="onFilterChanged"
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
          outlined
          solo
          flat
          dense
          clearable
          @input="onTextFilterChanged"
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

<script>
import _ from "lodash";

import { ReviewStatusRuleFilter } from "@cc/report-server-types";

import { ReviewStatusMixin } from "@/mixins";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import SelectReviewStatus from "./SelectReviewStatus";

export default {
  name: "ReviewStatusRuleFilter",
  components: { SelectReviewStatus, TooltipHelpIcon },
  mixins: [ ReviewStatusMixin ],
  props: {
    bus: { type: Object, required: true }
  },
  data() {
    const queries = this.$router.currentRoute.query;
    const reportHash = queries["report-hash"];
    const noAssociatedReports =
      (queries["no-associated-reports"] && true) || false;
    const reviewStatus = queries["review-status"]
      ? this.reviewStatusFromStringToCode(queries["review-status"]) : null;
    const author = queries["author"];

    return {
      author,
      reportHash,
      reviewStatus,
      noAssociatedReports
    };
  },
  computed: {
    status() {
      if (this.reviewStatus !== null) {
        return this.reviewStatusFromCodeToString(this.reviewStatus);
      }
      return null;
    },

    filter() {
      if (
        !this.reportHash &&
        !this.noAssociatedReports &&
        !this.reviewStatus &&
        !this.author
      ) return;

      const filter = new ReviewStatusRuleFilter();
      filter.reportHashes = this.reportHash ? [ `${this.reportHash}*` ] : null;
      filter.authors = this.author ? [ `${this.author}*` ] : null;
      filter.reviewStatuses =
        this.reviewStatus !== null ? [ this.reviewStatus ] : null;
      filter.noAssociatedReports = this.noAssociatedReports;

      return filter;
    }
  },
  mounted() {
    this.onFilterChanged();

    this.bus.$on("clear", () => {
      this.reportHash = null;
      this.author = null;
      this.reviewStatus = null;
      this.noAssociatedReports = null;

      this.onFilterChanged();
    });
  },
  methods: {
    onTextFilterChanged: _.debounce(function () {
      this.onFilterChanged();
    }, 400),

    onFilterChanged () {
      this.$emit("on:filter", this.filter);
      this.updateUrl({
        "report-hash": this.reportHash ? this.reportHash : undefined,
        "author": this.author ? this.author : undefined,
        "no-associated-reports": this.noAssociatedReports ? "on" : undefined,
        "review-status": this.status !== null ? this.status : undefined
      });
    },

    updateUrl(params) {
      this.$router.replace({
        query: {
          ...this.$route.query,
          ...params
        }
      }).catch(() => {});
    }
  }
};
</script>
