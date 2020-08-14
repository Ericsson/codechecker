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
    item-key="name"
    show-expand
    :expanded.sync="expanded"
    @item-expanded="itemExpanded"
  >
    <template v-slot:header.name="{ header }">
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

    <template #item.name="{ item }">
      <source-component-tooltip :value="item.value">
        <template v-slot="{ on }">
          <span v-on="on">
            <router-link
              :to="{ name: 'reports', query: {
                ...$router.currentRoute.query,
                'source-component': item.name
              }}"
            >
              {{ item.name }}
            </router-link>
          </span>
        </template>
      </source-component-tooltip>
    </template>

    <template #item.unreviewed="{ item }">
      <router-link
        v-if="item.unreviewed"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.name,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.UNREVIEWED)
        }}"
      >
        {{ item.unreviewed }}
      </router-link>
    </template>

    <template #item.confirmed="{ item }">
      <router-link
        v-if="item.confirmed"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.name,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.CONFIRMED)
        }}"
      >
        {{ item.confirmed }}
      </router-link>
    </template>

    <template #item.falsePositive="{ item }">
      <router-link
        v-if="item.falsePositive"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.name,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.FALSE_POSITIVE)
        }}"
      >
        {{ item.falsePositive }}
      </router-link>
    </template>

    <template #item.intentional="{ item }">
      <router-link
        v-if="item.intentional"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.name,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.INTENTIONAL)
        }}"
      >
        {{ item.intentional }}
      </router-link>
    </template>

    <template #item.reports="{ item }">
      <router-link
        v-if="item.reports"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'source-component': item.name
        }}"
      >
        {{ item.reports }}
      </router-link>
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

export default {
  name: "ComponentStatisticsTable",
  components: {
    CheckerStatisticsTable,
    DetectionStatusIcon,
    ReviewStatusIcon,
    SourceComponentTooltip
  },
  mixins: [ ReviewStatusMixin ],
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false }
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
          value: "name",
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
        const item = this.items.find(i => i.name === e.name);
        this.itemExpanded({ item : item });
      });
    }
  },
  methods: {
    async itemExpanded(expandedItem) {
      if (expandedItem.item.checkerStatistics) return;

      expandedItem.item.loading = true;

      const component = expandedItem.item.name;
      const runIds = this.runIds;
      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter["componentNames"] = [ component ];

      const stats = await getCheckerStatistics(runIds, reportFilter);
      expandedItem.item.checkerStatistics = stats.map(stat => ({
        ...stat,
        $queryParams: { "source-component": component }
      }));
      expandedItem.item.loading = false;
    },
  }
};
</script>
