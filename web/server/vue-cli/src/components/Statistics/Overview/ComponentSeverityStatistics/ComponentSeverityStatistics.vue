<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <component-severity-statistics-table
          :items="statistics"
          :loading="loading"
          :filters="statisticsFilters"
          :total-columns="totalColumns"
        >
          <template
            v-for="item in [
              ['critical', Severity.CRITICAL],
              ['high', Severity.HIGH],
              ['medium', Severity.MEDIUM],
              ['low', Severity.LOW],
              ['style', Severity.STYLE],
              ['unspecified', Severity.UNSPECIFIED],
            ]"
            v-slot:[`header.${item[0]}.count`]="{ header }"
          >
            <span :key="item[0]">
              <severity-icon :status="item[1]" :size="16" />
              {{ header.text }}
            </span>
          </template>

          <template
            v-for="i in [
              ['critical', Severity.CRITICAL],
              ['high', Severity.HIGH],
              ['medium', Severity.MEDIUM],
              ['low', Severity.LOW],
              ['style', Severity.STYLE],
              ['unspecified', Severity.UNSPECIFIED],
            ]"
            v-slot:[`item.${i[0]}.count`]="{ item }"
          >
            <span :key="i[0]">
              <router-link
                v-if="item[i[0]].count"
                :to="{ name: 'reports', query: {
                  ...$router.currentRoute.query,
                  ...(item.$queryParams || {}),
                  'source-component': item.component,
                  'severity': severityFromCodeToString(i[1])
                }}"
              >
                {{ item[i[0]].count }}
              </router-link>

              <report-diff-count
                :num-of-new-reports="item[i[0]].new"
                :num-of-resolved-reports="item[i[0]].resolved"
              />
            </span>
          </template>

          <template v-slot:header.reports.count="{ header }">
            <detection-status-icon
              :status="DetectionStatus.UNRESOLVED"
              :size="16"
              left
            />
            {{ header.text }}
          </template>
        </component-severity-statistics-table>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card flat>
          <v-row justify="center">
            <v-overlay
              :value="loading"
              :absolute="true"
              :opacity="0.2"
            >
              <v-progress-circular
                indeterminate
                size="64"
              />
            </v-overlay>
          </v-row>

          <component-severity-statistics-chart
            :loading="loading"
            :statistics="statistics"
          />
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import {
  DetectionStatus,
  ReportFilter,
  Severity
} from "@cc/report-server-types";
import { SeverityMixin } from "@/mixins";
import { DetectionStatusIcon, SeverityIcon } from "@/components/Icons";
import {
  ComponentStatistics,
  ReportDiffCount,
  initDiffField
} from "@/components/Statistics";

import ComponentSeverityStatisticsChart from
  "./ComponentSeverityStatisticsChart";
import ComponentSeverityStatisticsTable from
  "./ComponentSeverityStatisticsTable";

export default {
  name: "ComponentSeverityStatistics",
  components: {
    ComponentSeverityStatisticsChart,
    ComponentSeverityStatisticsTable,
    DetectionStatusIcon,
    ReportDiffCount,
    SeverityIcon
  },
  mixins: [ ComponentStatistics, SeverityMixin ],
  data() {
    const fieldsToUpdate = [ "critical", "high", "medium", "low", "style",
      "unspecified", "reports" ];

    return {
      DetectionStatus,
      Severity,
      totalColumns: fieldsToUpdate,
      fieldsToUpdate: fieldsToUpdate
    };
  },
  methods: {
    getComponentStatistics(component, runIds, reportFilter, cmpData) {
      const filter = new ReportFilter(reportFilter);
      filter["severity"] = null;
      filter["componentNames"] = [ component.name ];

      return new Promise(resolve =>
        ccService.getClient().getSeverityCounts(runIds, filter, cmpData,
          handleThriftError(res => resolve(res))));
    },

    initStatistics(components) {
      this.statistics = components.map(component => ({
        component   : component.name,
        value       : component.value || component.description,
        reports     : initDiffField(undefined),
        critical    : initDiffField(undefined),
        high        : initDiffField(undefined),
        medium      : initDiffField(undefined),
        low         : initDiffField(undefined),
        style       : initDiffField(undefined),
        unspecified : initDiffField(undefined)
      }));
    },

    async getStatistics(component, runIds, reportFilter, cmpData) {
      const res = await this.getComponentStatistics(component, runIds,
        reportFilter, cmpData);

      const reports = Object.keys(res).reduce((acc, curr) => {
        acc += res[curr].toNumber();
        return acc;
      }, 0);

      return {
        component   : component.name,
        value       : component.value || component.description,
        reports     : initDiffField(reports),
        critical    : initDiffField(res[Severity.CRITICAL]),
        high        : initDiffField(res[Severity.HIGH]),
        medium      : initDiffField(res[Severity.MEDIUM]),
        low         : initDiffField(res[Severity.LOW]),
        style       : initDiffField(res[Severity.STYLE]),
        unspecified : initDiffField(res[Severity.UNSPECIFIED])
      };
    },
  }
};
</script>
