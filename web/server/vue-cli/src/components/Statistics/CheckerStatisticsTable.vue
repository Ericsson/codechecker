<template>
  <v-data-table
    :headers="headers"
    :items="items"
    :disable-pagination="true"
    :hide-default-footer="true"
    :must-sort="true"
    sort-by="severity"
    sort-desc
    :loading="loading"
    :mobile-breakpoint="1000"
    class="elevation-1"
    loading-text="Loading checker statistics..."
    item-key="checker"
  >
    <template v-slot:header.unreviewed.count="{ header }">
      <review-status-icon
        :status="ReviewStatus.UNREVIEWED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.confirmed.count="{ header }">
      <review-status-icon
        :status="ReviewStatus.CONFIRMED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.falsePositive.count="{ header }">
      <review-status-icon
        :status="ReviewStatus.FALSE_POSITIVE"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.intentional.count="{ header }">
      <review-status-icon
        :status="ReviewStatus.INTENTIONAL"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template v-slot:header.reports.count="{ header }">
      <detection-status-icon
        :status="DetectionStatus.UNRESOLVED"
        :size="16"
        left
      />
      {{ header.text }}
    </template>

    <template #item.checker="{ item }">
      <router-link
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker
        }}"
      >
        {{ item.checker }}
      </router-link>
    </template>

    <template #item.severity="{ item }">
      <router-link
        class="severity"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'severity': severityFromCodeToString(
            item.severity)
        }}"
      >
        <severity-icon :status="item.severity" />
      </router-link>
    </template>

    <template #item.unreviewed.count="{ item }">
      <router-link
        v-if="item.unreviewed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.UNREVIEWED)
        }}"
      >
        {{ item.unreviewed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.unreviewed.new"
        :num-of-resolved-reports="item.unreviewed.resolved"
      />
    </template>

    <template #item.confirmed.count="{ item }">
      <router-link
        v-if="item.confirmed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.CONFIRMED)
        }}"
      >
        {{ item.confirmed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.confirmed.new"
        :num-of-resolved-reports="item.confirmed.resolved"
      />
    </template>

    <template #item.falsePositive.count="{ item }">
      <router-link
        v-if="item.falsePositive.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.FALSE_POSITIVE)
        }}"
      >
        {{ item.falsePositive.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.falsePositive.new"
        :num-of-resolved-reports="item.falsePositive.resolved"
      />
    </template>

    <template #item.intentional.count="{ item }">
      <router-link
        v-if="item.intentional.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.INTENTIONAL)
        }}"
      >
        {{ item.intentional.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.intentional.new"
        :num-of-resolved-reports="item.intentional.resolved"
      />
    </template>

    <template #item.reports.count="{ item }">
      <router-link
        v-if="item.reports.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker
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
        <td class="text-center" colspan="2">
          <strong>Total</strong>
        </td>
        <td
          v-for="col in ['unreviewed', 'confirmed', 'falsePositive',
                         'intentional', 'reports']"
          :key="col"
          class="text-center"
        >
          <strong>{{ total[col] }}</strong>
        </td>
      </tr>
    </template>
  </v-data-table>
</template>

<script>
import { DetectionStatus, ReviewStatus } from "@cc/report-server-types";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";

import { ReviewStatusMixin, SeverityMixin } from "@/mixins";
import ReportDiffCount from "./ReportDiffCount";

export default {
  name: "CheckerStatisticsTable",
  components: {
    DetectionStatusIcon,
    ReportDiffCount,
    ReviewStatusIcon,
    SeverityIcon
  },
  mixins: [ ReviewStatusMixin, SeverityMixin ],
  props: {
    items: { type: Array, required: true },
    loading: { type: Boolean, default: false }
  },
  data() {
    return {
      ReviewStatus,
      DetectionStatus,
      headers: [
        {
          text: "Checker",
          value: "checker"
        },
        {
          text: "Severity",
          value: "severity",
          align: "center"
        },
        {
          text: "Unreviewed",
          value: "unreviewed.count",
          align: "center"
        },
        {
          text: "Confirmed bug",
          value: "confirmed.count",
          align: "center"
        },
        {
          text: "False positive",
          value: "falsePositive.count",
          align: "center"
        },
        {
          text: "Intentional",
          value: "intentional.count",
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
      const cols = [ "unreviewed", "confirmed", "falsePositive", "intentional",
        "reports" ];

      const initVal = cols.reduce((acc, curr) => {
        acc[curr] = 0;
        return acc;
      }, {});

      return this.items.reduce((total, curr) => {
        cols.forEach(c => total[c] += curr[c].count);
        return total;
      }, initVal);
    }
  },
};
</script>

<style lang="scss" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
