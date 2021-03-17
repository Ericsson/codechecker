<template>
  <v-data-table
    :disable-pagination="true"
    :hide-default-footer="true"
    :must-sort="true"
    class="elevation-0"
    v-bind="{ ...$props, ...$attrs }"
    v-on="$listeners"
  >
    <template v-slot:header.component="{ header }">
      <v-icon size="16">
        mdi-puzzle-outline
      </v-icon>
      {{ header.text }}
    </template>

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

    <template v-slot:header.outstanding.count="{ header }">
      <v-icon color="red" :size="16">
        mdi-sigma
      </v-icon>
      {{ header.text }}<br>
      <span class="pl-4">(Unreviewed + Confirmed)</span>
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

    <template v-slot:header.suppressed.count="{ header }">
      <v-icon color="grey" :size="16">
        mdi-sigma
      </v-icon>
      {{ header.text }}<br>
      <span class="pl-4">(False positive + Intentional)</span>
    </template>

    <template v-slot:header.reports.count="{ header }">
      <detection-status-icon
        :status="DetectionStatus.UNRESOLVED"
        :size="16"
        left
      />
      {{ header.text }}<br>
      <span class="pl-4">(Outstanding + Suppressed)</span>
    </template>

    <template #item.checker="{ item }">
      <div>
        <router-link
          class="checker-name"
          :to="{ name: 'reports', query: {
            ...$router.currentRoute.query,
            ...(item.$queryParams || {}),
            'checker-name': item.checker
          }}"
        >
          {{ item.checker }}
        </router-link>
      </div>
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

    <template #item.severity="{ item }">
      <router-link
        class="severity"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          'checker-name': item.checker,
          'severity': severityFromCodeToString(item.severity)
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
          ...getBaseQueryParams(item),
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.UNREVIEWED)
        }}"
      >
        {{ item.unreviewed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.unreviewed.new"
        :num-of-resolved-reports="item.unreviewed.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.confirmed.count="{ item }">
      <router-link
        v-if="item.confirmed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.CONFIRMED)
        }}"
      >
        {{ item.confirmed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.confirmed.new"
        :num-of-resolved-reports="item.confirmed.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.outstanding.count="{ item }">
      <router-link
        v-if="item.outstanding.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
          'review-status': [
            reviewStatusFromCodeToString(ReviewStatus.UNREVIEWED),
            reviewStatusFromCodeToString(ReviewStatus.CONFIRMED)
          ]
        }}"
      >
        {{ item.outstanding.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.outstanding.new"
        :num-of-resolved-reports="item.outstanding.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.falsePositive.count="{ item }">
      <router-link
        v-if="item.falsePositive.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.FALSE_POSITIVE)
        }}"
      >
        {{ item.falsePositive.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.falsePositive.new"
        :num-of-resolved-reports="item.falsePositive.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.intentional.count="{ item }">
      <router-link
        v-if="item.intentional.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
          'review-status': reviewStatusFromCodeToString(
            ReviewStatus.INTENTIONAL)
        }}"
      >
        {{ item.intentional.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.intentional.new"
        :num-of-resolved-reports="item.intentional.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.suppressed.count="{ item }">
      <router-link
        v-if="item.suppressed.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
          'review-status': [
            reviewStatusFromCodeToString(ReviewStatus.FALSE_POSITIVE),
            reviewStatusFromCodeToString(ReviewStatus.INTENTIONAL)
          ]
        }}"
      >
        {{ item.suppressed.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.suppressed.new"
        :num-of-resolved-reports="item.suppressed.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template #item.reports.count="{ item }">
      <router-link
        v-if="item.reports.count"
        :to="{ name: 'reports', query: {
          ...$router.currentRoute.query,
          ...(item.$queryParams || {}),
          ...getBaseQueryParams(item),
        }}"
      >
        {{ item.reports.count }}
      </router-link>

      <report-diff-count
        :num-of-new-reports="item.reports.new"
        :num-of-resolved-reports="item.reports.resolved"
        :extra-query-params="getBaseQueryParams(item)"
      />
    </template>

    <template slot="body.append">
      <tr>
        <td class="text-center" :colspan="colspan">
          <strong>Total</strong>
        </td>
        <td
          v-for="col in totalColumns"
          :key="col"
          class="text-center"
        >
          <strong>{{ total[col] }}</strong>
        </td>
      </tr>
    </template>

    <template
      v-for="(_, slot) of $scopedSlots"
      v-slot:[slot]="scope"
    >
      <slot :name="slot" v-bind="scope" />
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
import { SourceComponentTooltip } from "@/components/Report/SourceComponent";
import ReportDiffCount from "./ReportDiffCount";

export default {
  name: "ReviewStatusStatisticsTable",
  components: {
    DetectionStatusIcon,
    ReportDiffCount,
    ReviewStatusIcon,
    SeverityIcon,
    SourceComponentTooltip
  },
  mixins: [ ReviewStatusMixin, SeverityMixin ],
  props: {
    items: { type: Array, required: true },
    colspan: { type: Number, default: 2 },
    totalColumns: {
      type: Array,
      default: () => [ "unreviewed", "confirmed", "outstanding",
        "falsePositive", "intentional", "suppressed","reports" ]
    }
  },
  data() {
    return {
      ReviewStatus,
      DetectionStatus
    };
  },
  computed: {
    total() {
      const initVal = this.totalColumns.reduce((acc, curr) => {
        acc[curr] = 0;
        return acc;
      }, {});

      return this.items.reduce((total, curr) => {
        this.totalColumns.forEach(c => total[c] += curr[c].count);
        return total;
      }, initVal);
    }
  },
  methods: {
    getBaseQueryParams({ checker, component, severity }) {
      const query = {};

      if (checker)
        query["checker-name"] = checker;

      if (component)
        query["source-component"] = component;

      if (severity)
        query["severity"] = this.severityFromCodeToString(severity);

      return query;
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep table {
  border: thin solid rgba(0, 0, 0, 0.12);
}

::v-deep a {
  text-decoration: none;

  &:not(.severity):hover {
    text-decoration: underline;
  }
}
</style>