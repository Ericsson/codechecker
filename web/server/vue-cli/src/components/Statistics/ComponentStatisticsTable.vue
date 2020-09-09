<template>
  <v-data-table
    :headers="headers"
    :items="items"
    :disable-pagination="true"
    :hide-default-footer="true"
    :loading="loading"
    :mobile-breakpoint="1000"
    class="elevation-1"
    loading-text="Loading component statistics..."
    no-data-text="No component statistics available"
    item-key="component"
    show-expand
    :expanded.sync="expanded"
    @item-expanded="itemExpanded"
  >
    <template v-slot:header.component="{ header }">
      <v-icon size="16">
        mdi-puzzle-outline
      </v-icon>
      {{ header.text }}
    </template>

    <template v-slot:header.unreviewed="{ header }">
      <review-status-icon
        :status="ReviewStatus.UNREVIEWED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.confirmed="{ header }">
      <review-status-icon
        :status="ReviewStatus.CONFIRMED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.falsePositive="{ header }">
      <review-status-icon
        :status="ReviewStatus.FALSE_POSITIVE"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.intentional="{ header }">
      <review-status-icon
        :status="ReviewStatus.INTENTIONAL"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.reports="{ header }">
      <detection-status-icon
        :status="DetectionStatus.UNRESOLVED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:expanded-item="{ item }">
      <td
        class="pa-0"
        :colspan="headers.length"
      >
        <v-card flat tile>
          <v-card-text v-if="item.loading || !item.checkerStatistics">
            Loading...
            <v-progress-linear
              indeterminate
              class="mb-0"
            />
          </v-card-text>

          <checker-statistics-table
            v-else
            :items="item.checkerStatistics"
            :loading="item.loading"
          />
        </v-card>
      </td>
    </template>

    <template #item.component="{ item }">
      <source-component-tooltip :value="item.value">
        <template v-slot="{ on }">
          <span v-on="on">
            <router-link
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'source-component': item.component
              }}"
            >
              {{ item.component }}
            </router-link>
          </span>
        </template>
      </source-component-tooltip>
    </template>

    <template #item.unreviewed="{ item }">
      <router-link
        v-if="item.unreviewed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.UNREVIEWED)
        }}"
      >
        {{ item.unreviewed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.unreviewed.new"
        :num-of-resolved-reports="item.unreviewed.resolved"
        :extra-query-params="{
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.UNREVIEWED)
        }"
      />
    </template>

    <template #item.confirmed="{ item }">
      <router-link
        v-if="item.confirmed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.CONFIRMED)
        }}"
      >
        {{ item.confirmed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.confirmed.new"
        :num-of-resolved-reports="item.confirmed.resolved"
        :extra-query-params="{
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.CONFIRMED)
        }"
      />
    </template>

    <template #item.falsePositive="{ item }">
      <router-link
        v-if="item.falsePositive.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.FALSE_POSITIVE)
        }}"
      >
        {{ item.falsePositive.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.falsePositive.new"
        :num-of-resolved-reports="item.falsePositive.resolved"
        :extra-query-params="{
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.FALSE_POSITIVE)
        }"
      />
    </template>

    <template #item.intentional="{ item }">
      <router-link
        v-if="item.intentional.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.INTENTIONAL)
        }}"
      >
        {{ item.intentional.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.intentional.new"
        :num-of-resolved-reports="item.intentional.resolved"
        :extra-query-params="{
          'source-component': item.component,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.INTENTIONAL)
        }"
      />
    </template>

    <template #item.reports="{ item }">
      <router-link
        v-if="item.reports.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.component
        }}"
      >
        {{ item.reports.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.reports.new"
        :num-of-resolved-reports="item.reports.resolved"
        :extra-query-params="{
          'source-component': item.component
        }"
      />
    </template>
  </v-data-table>
</template>

<script>
import {
  DetectionStatus,
  ReportFilter,
  ReviewStatus
} from "@cc/report-server-types";
import {
  DetectionStatusIcon,
  ReviewStatusIcon
} from "@/components/Icons";

import { ReviewStatusMixin } from "@/mixins";

import { SourceComponentTooltip } from "@/components/Report/SourceComponent";

import CheckerStatisticsTable from "./CheckerStatisticsTable";
import { getCheckerStatistics } from "./StatisticsHelper";
import ReportDiffCount from "./ReportDiffCount";

export default {
  name: "ComponentStatisticsTable",
  components: {
    CheckerStatisticsTable,
    DetectionStatusIcon,
    ReportDiffCount,
    ReviewStatusIcon,
    SourceComponentTooltip
  },
  mixins: [ ReviewStatusMixin ],
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false },
    filters: { type: Object, default: () => {} }
  },
  data() {
    return {
      ReviewStatus,
      DetectionStatus,
      expanded: [],
      headers: [
        {
          text: "",
          value: "data-table-expand"
        },
        {
          text: "Component",
          value: "component",
          align: "center"
        },
        {
          text: "Unreviewed",
          value: "unreviewed",
          align: "center"
        },
        {
          text: "Confirmed bug",
          value: "confirmed",
          align: "center"
        },
        {
          text: "False positive",
          value: "falsePositive",
          align: "center"
        },
        {
          text: "Intentional",
          value: "intentional",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports",
          align: "center"
        }
      ],
    };
  },
  watch: {
    loading() {
      if (this.loading) return;

      this.expanded.forEach(e => {
        const item = this.items.find(i => i.component === e.component);
        this.itemExpanded({ item : item });
      });
    }
  },
  methods: {
    async itemExpanded(expandedItem) {
      if (expandedItem.item.checkerStatistics) return;

      expandedItem.item.loading = true;

      const component = expandedItem.item.component;
      const runIds = this.filters.runIds;
      const reportFilter = new ReportFilter(this.filters.reportFilter);
      reportFilter["componentNames"] = [ component ];
      const cmpData = this.filters.cmpData;

      const stats = await getCheckerStatistics(runIds, reportFilter, cmpData);
      expandedItem.item.checkerStatistics = stats.map(stat => ({
        ...stat,
        $queryParams: { "source-component": component }
      }));
      expandedItem.item.loading = false;
    },
  }
};
</script>
