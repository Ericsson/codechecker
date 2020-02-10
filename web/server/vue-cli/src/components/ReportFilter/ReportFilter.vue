<template>
  <div>
    <!--
      'refs' becomes an Array if used inside a v-for. This is the reason
      why we use this
    -->
    <v-list
      v-for="i in 1"
      :key="i"
      dense
      flat
      tile
      elevation="0"
    >
      <v-list-item>
        <v-list-item-action class="mr-5">
          <clear-all-filters />
        </v-list-item-action>

        <v-spacer />

        <v-list-item-content>
          <report-count ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <unique-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <report-hash-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <v-expansion-panels v-model="activeBaselinePanelId">
            <v-expansion-panel>
              <v-expansion-panel-header>BASELINE</v-expansion-panel-header>
              <v-expansion-panel-content>
                <baseline-run-filter ref="filters" />
                <baseline-tag-filter ref="filters" />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <v-expansion-panels v-model="activeNewcheckPanelId">
            <v-expansion-panel>
              <v-expansion-panel-header>NEWCHECK</v-expansion-panel-header>
              <v-expansion-panel-content>
                <newcheck-run-filter ref="filters" />
                <newcheck-tag-filter ref="filters" />
                <newcheck-diff-type-filter ref="filters" />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <review-status-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <detection-status-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <severity-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <bug-path-length-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <detection-date-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <file-path-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <source-component-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <checker-name-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <checker-message-filter ref="filters" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <remove-filtered-reports />
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
import {
  UniqueFilter,
  ReportHashFilter,
  BaselineRunFilter,
  BaselineTagFilter,
  NewcheckDiffTypeFilter,
  NewcheckRunFilter,
  NewcheckTagFilter,
  ReviewStatusFilter,
  DetectionStatusFilter,
  SeverityFilter,
  DetectionDateFilter,
  FilePathFilter,
  SourceComponentFilter,
  CheckerNameFilter,
  CheckerMessageFilter,
  BugPathLengthFilter
} from "./Filters";

import ClearAllFilters from "./ClearAllFilters";
import RemoveFilteredReports from "./RemoveFilteredReports";
import ReportCount from "./ReportCount";

export default {
  name: "ReportFilter",
  components: {
    ClearAllFilters,
    ReportCount,
    UniqueFilter,
    ReportHashFilter,
    BaselineRunFilter,
    BaselineTagFilter,
    NewcheckDiffTypeFilter,
    NewcheckRunFilter,
    NewcheckTagFilter,
    ReviewStatusFilter,
    DetectionStatusFilter,
    SeverityFilter,
    DetectionDateFilter,
    FilePathFilter,
    SourceComponentFilter,
    CheckerNameFilter,
    CheckerMessageFilter,
    RemoveFilteredReports,
    BugPathLengthFilter
  },
  props: {
    afterUrlInit: { type: Function, default: () => {} }
  },

  data() {
    return {
      activeBaselinePanelId: 0,
      activeNewcheckPanelId: -1
    };
  },

  mounted() {
    this.initByUrl();
  },

  beforeUpdate() {
    // TODO: init by url if component is not initialized.
  },

  methods: {
    initByUrl() {
      const filters = this.$refs.filters;

      // Init all filters by URL parameters.
      const results = filters.map((filter) => {
        return filter.initByUrl();
      });

      // If all filters are initalized call a post function.
      Promise.all(results).then(() => {
        filters.map((filter) => {
          return filter.afterUrlInit();
        });
        this.afterUrlInit();
      });
    }
  }
}
</script>

<style lang="scss">
.v-list-item {
  .v-expansion-panel::before {
    box-shadow: none;
  }
}
</style>
