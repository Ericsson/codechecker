<template>
  <v-data-table
    :headers="headers"
    :items="items"
    :hide-default-footer="true"
    :must-sort="true"
    :loading="loading"
    loading-text="Loading severity statistics..."
    item-key="severity"
  >
    <template v-slot:header.reports.count="{ header }">
      <detection-status-icon
        :status="DetectionStatus.UNRESOLVED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template #item.severity="{ item }">
      <router-link
        class="severity"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'severity': severityFromCodeToString(
            item.severity)
        }}"
      >
        <severity-icon :status="item.severity" />
      </router-link>
    </template>

    <template #item.reports.count="{ item }">
      <router-link
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          'severity': severityFromCodeToString(
            item.severity)
        }}"
      >
        {{ item.reports.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.reports.new"
        :num-of-resolved-reports="item.reports.resolved"
      />
    </template>

    <template slot="body.append">
      <tr>
        <td class="text-center">
          <strong>Total</strong>
        </td>
        <td class="text-center">
          <strong>{{ total.reports }}</strong>
        </td>
      </tr>
    </template>
  </v-data-table>
</template>

<script>
import { DetectionStatus } from "@cc/report-server-types";
import { DetectionStatusIcon, SeverityIcon } from "@/components/Icons";
import { SeverityMixin } from "@/mixins";
import ReportDiffCount from "./ReportDiffCount";

export default {
  name: "SeverityStatisticsTable",
  components: {
    DetectionStatusIcon,
    ReportDiffCount,
    SeverityIcon
  },
  mixins: [ SeverityMixin ],
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false }
  },

  data() {
    return {
      DetectionStatus,
      headers: [
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports.count",
          align: "center"
        }
      ]
    };
  },

  computed: {
    total() {
      return {
        reports: this.items.reduce((total, curr) =>
          curr.reports.count + total, 0)
      };
    }
  },
};
</script>
