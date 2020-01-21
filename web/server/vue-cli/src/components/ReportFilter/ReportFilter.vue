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
          <clear-all-filters :report-filter="reportFilter" />
        </v-list-item-action>

        <v-spacer />

        <v-list-item-content>
          <report-count
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <unique-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <report-hash-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <baseline-filter :report-filter="reportFilter" />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <newcheck-filter />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <review-status-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <detection-status-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <severity-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <detection-date-filter />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <file-path-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <source-component-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <checker-name-filter
            ref="filters"
            :report-filter="reportFilter"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item>
        <v-list-item-content>
          <checker-message-filter
            ref="filters"
            :report-filter="reportFilter"
          />
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
  VList,
  VListItem,
  VListItemAction,
  VListItemContent
} from "Vuetify/VList";
import VSpacer from "Vuetify/VGrid/VSpacer";

import {
  UniqueFilter,
  ReportHashFilter,
  BaselineFilter,
  NewcheckFilter,
  ReviewStatusFilter,
  DetectionStatusFilter,
  SeverityFilter,
  DetectionDateFilter,
  FilePathFilter,
  SourceComponentFilter,
  CheckerNameFilter,
  CheckerMessageFilter
} from './Filters';

import ClearAllFilters from './ClearAllFilters';
import RemoveFilteredReports from './RemoveFilteredReports';
import ReportCount from './ReportCount';

export default {
  name: 'ReportFilter',
  components: {
    VList, VListItem, VListItemAction, VListItemContent, VSpacer,
    ClearAllFilters,
    ReportCount,
    UniqueFilter,
    ReportHashFilter,
    BaselineFilter,
    NewcheckFilter,
    ReviewStatusFilter,
    DetectionStatusFilter,
    SeverityFilter,
    DetectionDateFilter,
    FilePathFilter,
    SourceComponentFilter,
    CheckerNameFilter,
    CheckerMessageFilter,
    RemoveFilteredReports
  },
  props: {
    runIds: { type: Array, required: true },
    reportFilter: { type: Object, required: true },
    cmpData: { required: true, validator: v => typeof v === 'object' },
    afterUrlInit: { type: Function, default: () => {} }
  },

  mounted() {
    this.initByUrl();
  },

  beforeUpdate() {
    this.initByUrl();
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
