<template>
  <v-list
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
        <report-count />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <unique-filter :report-filter="reportFilter" />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <report-hash-filter :report-filter="reportFilter" />
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
        <review-status-filter />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <detection-status-filter />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <severity-filter :report-filter="reportFilter" />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <detection-date-filter />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <file-path-filter :report-filter="reportFilter" />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <source-component-filter />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <checker-name-filter :report-filter="reportFilter" />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <checker-message-filter :report-filter="reportFilter" />
      </v-list-item-content>
    </v-list-item>

    <v-list-item>
      <v-list-item-content>
        <remove-filtered-reports />
      </v-list-item-content>
    </v-list-item>
  </v-list>
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
    cmpData: { required: true, validator: v => typeof v === 'object' }
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
