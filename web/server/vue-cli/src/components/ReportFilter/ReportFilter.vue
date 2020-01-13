<template>
  <div>
    <clear-all-filters />
    <report-count />
    <unique-filter :report-filter="reportFilter" />
    <report-hash-filter :report-filter="reportFilter" />
    <baseline-filter />
    <newcheck-filter />
    <review-status-filter />
    <detection-status-filter />
    <severity-filter />
    <detection-date-filter />
    <file-path-filter />
    <source-component-filter />
    <checker-name-filter />
    <checker-message-filter />
    <remove-filtered-reports />
  </div>
</template>

<script>
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
