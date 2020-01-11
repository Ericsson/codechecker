<template>
  <div>
    <clear-all-filters />
    <report-count />
    <unique-filter />
    <report-hash-filter />
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
import ClearAllFilters from './ClearAllFilters';
import ReportCount from './ReportCount';
import UniqueFilter from './UniqueFilter';
import ReportHashFilter from './ReportHashFilter';
import BaselineFilter from './BaselineFilter';
import NewcheckFilter from './NewcheckFilter';
import ReviewStatusFilter from './ReviewStatusFilter';
import DetectionStatusFilter from './DetectionStatusFilter';
import SeverityFilter from './SeverityFilter';
import DetectionDateFilter from './DetectionDateFilter';
import FilePathFilter from './FilePathFilter';
import SourceComponentFilter from './SourceComponentFilter';
import CheckerNameFilter from './CheckerNameFilter';
import CheckerMessageFilter from './CheckerMessageFilter';
import RemoveFilteredReports from './RemoveFilteredReports';

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
  }
}
</script>
