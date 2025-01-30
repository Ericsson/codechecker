<template>
  <v-data-table
    :disable-pagination="true"
    :hide-default-footer="true"
    :custom-sort="customSort"
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

    <template #item.enabledInAllRuns="{ item }">
      <div v-if="item.enabledInAllRuns">
        <count-chips
          :num-good="item.enabledRunLength"
          :good-text="'Number of runs where checker was enabled'"
          :show-dividers="false"
          :show-zero-chips="false"
          @showing-good-click="$emit('enabled-click', 'enabled', item.checker)"
        />
      </div>
      <div v-else>
        <count-chips
          :num-good="item.enabledRunLength"
          :num-bad="item.disabledRunLength"
          :good-text="'Number of runs where checker was enabled'"
          :bad-text="'Number of runs where checker was disabled'"
          :show-dividers="false"
          :show-zero-chips="false"
          @showing-good-click="$emit('enabled-click', 'enabled', item.checker)"
          @showing-bad-click="$emit('enabled-click', 'disabled', item.checker)"
        />
      </div>
    </template>

    <template #item.closed="{ item }">
      <span v-if="item.closed">
        <router-link
          :to="{ name: 'reports', query: {
            ...uniqueMode,
            ...getBaseQueryParams(item),
            'report-status': reportStatusFromCodeToString(ReportStatus.CLOSED)
          }}"
        >
          {{ item.closed }}
        </router-link>
      </span>
      <span v-else>
        {{ item.closed }}
      </span>
    </template>

    <template #item.outstanding="{ item }">
      <span v-if="item.outstanding">
        <router-link
          :to="{ name: 'reports', query: {
            ...uniqueMode,
            ...getBaseQueryParams(item),
            'report-status': reportStatusFromCodeToString(
              ReportStatus.OUTSTANDING
            )
          }}"
        >
          {{ item.outstanding }}
        </router-link>
      </span>
      <span v-else>
        {{ item.outstanding }}
      </span>
    </template>

    <template #item.guidelineRules="{ item }">
      <div v-if="item.guidelineRules.length">
        <div 
          v-for="guidelineRule in item.guidelineRules"
          :key="guidelineRule.type"
        >
          <span class="type">
            {{ guidelineRule.type }}:
          </span>
          <span 
            v-for="rule in guidelineRule.rules"
            :key="rule"
            :style="getRuleStyle(guidelineRule)"
          >
            {{ rule }}
          </span>
        </div>
      </div>
    </template>
    
    <template #item.guidelineRule="{ item }">
      <a
        :href="item.guidelineUrl"
        target="_blank"
      >
        {{ item.guidelineRule }}
      </a>
    </template>

    <template 
      #item.checkers.name="{ item }"
    >
      <div 
        v-if="item.checkers && item.checkers.length === 0"
      >
        none
      </div>
      <div v-else class="guideline-statistics">
        <table>
          <tr v-for="checker in item.checkers" :key="checker.name">
            <td>
              <router-link
                :to="{ name: 'reports', query: {
                  ...$router.currentRoute.query,
                  ...(item.$queryParams || {}),
                  'checker-name': checker.name
                }}"
              >
                {{ checker.name }}
              </router-link>
            </td>
          </tr>
        </table>
      </div>
    </template>

    <template 
      #item.checkers.severity="{ item }"
    >
      <div 
        v-if="item.checkers && item.checkers.length === 0"
        class="text-center"
      >
        none
      </div>
      <div v-else class="guideline-statistics">
        <table>
          <tr v-for="checker in item.checkers" :key="checker.name">
            <td>
              <severity-icon :status="checker.severity" />
            </td>
          </tr>
        </table>
      </div>
    </template>

    <template 
      #item.checkers.enabledInAllRuns="{ item }"
    >
      <div 
        v-if="item.checkers && item.checkers.length === 0"
        class="text-center"
      >
        none
      </div>
      <div v-else class="guideline-statistics">
        <table>
          <tr v-for="checker in item.checkers" :key="checker.name">
            <td>
              <div v-if="checker.enabledInAllRuns">
                <count-chips
                  :num-good="checker.enabledRunLength"
                  :good-text="'Number of runs where checker was enabled'"
                  :show-dividers="false"
                  :show-zero-chips="false"
                  @showing-good-click="$emit(
                    'enabled-click', 'enabled', checker.name)"
                />
              </div>
              <div v-else-if="checker.enabledRunLength">
                <count-chips
                  :num-good="checker.enabledRunLength"
                  :num-bad="checker.disabledRunLength"
                  :good-text="'Number of runs where checker was enabled'"
                  :bad-text="'Number of runs where checker was disabled'"
                  :show-dividers="false"
                  :show-zero-chips="false"
                  @showing-good-click="$emit(
                    'enabled-click', 'enabled', checker.name)"
                  @showing-bad-click="$emit(
                    'enabled-click', 'disabled', checker.name)"
                />
              </div>
              <div v-else>
                <count-chips
                  :num-bad="checker.disabledRunLength"
                  :bad-text="'Number of runs where checker was disabled'"
                  :show-dividers="false"
                  :show-zero-chips="false"
                  @showing-bad-click="$emit(
                    'enabled-click', 'disabled', checker.name)"
                />
              </div>
            </td>
          </tr>
        </table>
      </div>
    </template>

    <template 
      #item.checkers.outstanding="{ item }"
    >
      <div 
        v-if="item.checkers && item.checkers.length === 0"
        class="text-center"
      >
        none
      </div>
      <div v-else class="guideline-statistics">
        <table>
          <tr v-for="checker in item.checkers" :key="checker.name">
            <td v-if="checker.outstanding">
              <router-link
                :to="{ name: 'reports', query: {
                  ...uniqueMode,
                  ...getBaseQueryParams({
                    checker: checker.name,
                    severity: checker.severity}),
                  'report-status': reportStatusFromCodeToString(
                    ReportStatus.OUTSTANDING
                  )
                }}"
              >
                {{ checker.outstanding }}
              </router-link>
            </td>
            <td v-else>
              {{ checker.outstanding }}
            </td>
          </tr>
        </table>
      </div>
    </template>

    <template 
      #item.checkers.closed="{ item }"
    >
      <div 
        v-if="item.checkers && item.checkers.length === 0"
        class="text-center"
      >
        none
      </div>
      <div v-else class="guideline-statistics">
        <table>
          <tr v-for="checker in item.checkers" :key="checker.name">
            <!-- <td>{{ checker.closed }}</td> -->
            <td v-if="checker.closed">
              <router-link
                :to="{ name: 'reports', query: {
                  ...uniqueMode,
                  ...getBaseQueryParams({
                    checker: checker.name,
                    severity: checker.severity}),
                  'report-status': reportStatusFromCodeToString(
                    ReportStatus.CLOSED)
                }}"
              >
                {{ checker.closed }}
              </router-link>
            </td>
            <td v-else>
              {{ checker.closed }}
            </td>
          </tr>
        </table>
      </div>
    </template>

    <template v-if="necessaryTotal" slot="body.append">
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
import {
  DetectionStatus,
  ReportStatus,
  ReviewStatus
} from "@cc/report-server-types";
import {
  DetectionStatusIcon,
  ReviewStatusIcon,
  SeverityIcon
} from "@/components/Icons";
import {
  DetectionStatusMixin,
  ReportStatusMixin,
  ReviewStatusMixin,
  SeverityMixin
} from "@/mixins";
import CountChips from "@/components/CountChips";
import { SourceComponentTooltip } from "@/components/Report/SourceComponent";
import ReportDiffCount from "./ReportDiffCount";

export default {
  name: "BaseStatisticsTable",
  components: {
    CountChips,
    DetectionStatusIcon,
    ReportDiffCount,
    ReviewStatusIcon,
    SeverityIcon,
    SourceComponentTooltip
  },
  mixins: [
    DetectionStatusMixin,
    ReportStatusMixin,
    ReviewStatusMixin,
    SeverityMixin
  ],
  props: {
    items: { type: Array, required: true },
    colspan: { type: Number, default: 2 },
    totalColumns: {
      type: Array,
      default: () => [ "unreviewed", "confirmed", "outstanding",
        "falsePositive", "intentional", "suppressed","reports" ]
    },
    necessaryTotal: { type: Boolean, default: false }
  },
  data() {
    return {
      DetectionStatus,
      ReportStatus,
      ReviewStatus
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
    },

    uniqueMode() {
      if ( this.$router.currentRoute.query["is-unique"] !== undefined ) {
        return {
          "is-unique": this.$router.currentRoute.query["is-unique"]
        };
      }
      else return {};
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
    },

    getRuleStyle(guidelineRule) {
      return {
        display: guidelineRule.rules.length > 1 ? "block" : "inline-block",
        "margin-left": guidelineRule.rules.length > 1 ? "1em" : "0"
      };
    },

    customSort(items, sortBy, sortDesc) {
      return items.sort((a, b) => {
        let result = 0;

        sortBy.forEach((column, index) => {
          if (result !== 0) return;

          let aValue, bValue;
          if (column.startsWith("checkers.")) {
            const prop = column.split("checkers.")[1];

            aValue = this.getNestedTableContent(
              a.checkers, prop, sortDesc[index]);
            bValue = this.getNestedTableContent(
              b.checkers, prop, sortDesc[index]);
          }
          else if (column.includes(".")) {
            const sub_columns = column.split(".");
            aValue = sub_columns.reduce((element, sub_coulmn) => (
              element && element[sub_coulmn] !== undefined
                ? element[sub_coulmn] : undefined), a);
            bValue = sub_columns.reduce((element, sub_coulmn) => (
              element && element[sub_coulmn] !== undefined
                ? element[sub_coulmn] : undefined), b);
          }
          else {
            aValue = a[column];
            bValue = b[column];
          }

          if (aValue < bValue) {
            result = sortDesc[index] ? 1 : -1;
          } else if (aValue > bValue) {
            result = sortDesc[index] ? -1 : 1;
          }
        });

        return result;
      });
    },

    getNestedTableContent(checkers, prop, descending) {
      if (checkers && checkers.length > 0) {
        if (prop === "enabledInAllRuns" ){
          const selectedChecker = checkers.reduce((max_or_min, current) => {
            return descending 
              ? (current["enabledRunLength"] > max_or_min["enabledRunLength"]
                ? current : max_or_min)
              : (current["enabledRunLength"] < max_or_min["enabledRunLength"]
                ? current : max_or_min);
          });
          return selectedChecker["enabledRunLength"];
        }
        else {
          const selectedChecker = checkers.reduce((max_or_min, current) => {
            return descending 
              ? (current[prop] > max_or_min[prop] ? current : max_or_min) 
              : (current[prop] < max_or_min[prop] ? current : max_or_min);
          });
          return selectedChecker[prop];
        }
      }
      return prop === "name" ? "" : -1;
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

.type {
  font-weight: bold;
}

.guideline-statistics table {
  width: 100%;
  height: 100%;
  border-collapse: collapse;
  border: none;
}

.guideline-statistics table td {
  padding: 2px;
  border-bottom: 1px solid #ddd;
}

.guideline-statistics table tr:last-child td {
  border-bottom: none;
}
</style>