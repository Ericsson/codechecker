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

    <template #item.unreviewed="{ item }">
      <router-link
        v-if="item.unreviewed"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
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
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
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
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
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
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
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
          ...(item.$queryParams || {}),
          'checker-name': item.checker
        }}"
      >
        {{ item.reports }}
      </router-link>
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

export default {
  name: "CheckerStatisticsTable",
  components: {
    DetectionStatusIcon,
    ReviewStatusIcon,
    SeverityIcon
  },
  mixins: [ ReviewStatusMixin, SeverityMixin ],
  props: {
    items: { type: Array, required: true },
    extraQueryParams: { type: Object, default: () => {} },
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
      ]
    };
  }
};
</script>

<style lang="scss" scoped>
::v-deep .severity {
  text-decoration: none;
}
</style>
