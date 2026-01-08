<template>
  <div>
    <!--
      'refs' becomes an Array if used inside a v-for. This is the reason
      why we use this
    -->
    <v-list
      v-for="i in 1"
      :key="i"
      dense
      flat
      tile
      elevation="0"
    >
      <v-list-item class="pl-1">
        <v-list-item-content class="mr-5">
          <clear-all-filters
            :namespace="namespace"
            @clear="clearAllFilters"
          />
        </v-list-item-content>
        <v-list-item-avatar :style="{width: 'auto'}">
          <report-count :value="reportCount" />
        </v-list-item-avatar>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content>
          <save-report-filter
            ref="filters"
            :namespace="namespace"
            @save_preset="getFilterPreset"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="unique-filter pl-1">
        <v-list-item-content>
          <unique-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item id="baseline-filters" class="pl-0">
        <v-list-item-content class="pa-0">
          <v-expansion-panels
            v-model="activeBaselinePanelId"
            hover
          >
            <v-expansion-panel>
              <v-expansion-panel-header
                class="pa-0 px-1 primary--text"
              >
                <header>
                  <b>BASELINE</b>
                </header>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="pa-1">
                <baseline-run-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />

                <v-divider />

                <baseline-open-reports-date-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list-item-content>
      </v-list-item>

      <v-list-item
        v-if="showCompareTo"
        id="compare-to-filters"
        class="pl-0"
      >
        <v-list-item-content class="pa-0">
          <v-expansion-panels
            v-model="activeCompareToPanelId"
            hover
          >
            <v-expansion-panel>
              <v-expansion-panel-header
                class="pa-0 px-1 primary--text"
              >
                <header>
                  <b>COMPARE TO</b>
                </header>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="pa-1">
                <compared-to-run-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />

                <v-divider />

                <compared-to-open-reports-date-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />

                <v-divider v-if="showDiffType" />

                <compared-to-diff-type-filter
                  v-if="showDiffType"
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <file-path-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <checker-name-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <severity-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <report-status-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider v-if="showReviewStatus" />

      <v-list-item
        v-if="showReviewStatus"
        class="pl-1"
      >
        <v-list-item-content class="pa-0">
          <review-status-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <detection-status-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <analyzer-name-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <source-component-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <cleanup-plan-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <checker-message-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item id="date-filters" class="pl-0">
        <v-list-item-content class="pa-0">
          <v-expansion-panels v-model="activeDatePanelId" hover>
            <v-expansion-panel>
              <v-expansion-panel-header
                class="pa-0 px-1"
              >
                <header>
                  <b>Dates</b>
                </header>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="pa-1">
                <detection-date-filter
                  id="detection-date-filter"
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />

                <v-divider class="mt-2" />

                <fix-date-filter
                  id="fix-date-filter"
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <report-hash-filter
            id="report-hash-filter"
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <bug-path-length-filter
            id="bug-path-length-filter"
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <testcase-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-divider v-if="showRemoveFilteredReports" />

      <v-list-item
        v-if="showRemoveFilteredReports"
        class="pl-1"
      >
        <v-list-item-content>
          <remove-filtered-reports
            class="mt-4"
            :namespace="namespace"
            @update="updateAllFilters"
          />
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
/* eslint-disable */
import { mapState } from "vuex";

import {
  AnalyzerNameFilter,
  BaselineOpenReportsDateFilter,
  BaselineRunFilter,
  BugPathLengthFilter,
  CheckerMessageFilter,
  CheckerNameFilter,
  CleanupPlanFilter,
  ComparedToDiffTypeFilter,
  ComparedToOpenReportsDateFilter,
  ComparedToRunFilter,
  DetectionDateFilter,
  DetectionStatusFilter,
  FilePathFilter,
  FixDateFilter,
  ReportHashFilter,
  ReportStatusFilter,
  ReviewStatusFilter,
  SeverityFilter,
  SourceComponentFilter,
  TestcaseFilter,
  UniqueFilter
} from "./Filters";

import ClearAllFilters from "./ClearAllFilters";
import RemoveFilteredReports from "./RemoveFilteredReports";
import ReportCount from "./ReportCount";
import SaveReportFilter from "./SaveReportFilter.vue";
import { ccService, handleThriftError } from "@cc-api";
import BaseSelectOptionFilterMixin from
  "./Filters/BaseSelectOptionFilter.mixin";

export default {
  name: "ReportFilter",
  components: {
    AnalyzerNameFilter,
    SaveReportFilter,
    ClearAllFilters,
    ReportCount,
    UniqueFilter,
    ReportHashFilter,
    BaselineRunFilter,
    BaselineOpenReportsDateFilter,
    CleanupPlanFilter,
    ComparedToDiffTypeFilter,
    ComparedToOpenReportsDateFilter,
    ComparedToRunFilter,
    ReviewStatusFilter,
    DetectionStatusFilter,
    SeverityFilter,
    DetectionDateFilter,
    FilePathFilter,
    FixDateFilter,
    SourceComponentFilter,
    CheckerNameFilter,
    CheckerMessageFilter,
    RemoveFilteredReports,
    BugPathLengthFilter,
    TestcaseFilter,
    ReportStatusFilter
  },
  mixins: [ BaseSelectOptionFilterMixin ],
  props: {
    namespace: { type: String, required: true },
    showCompareTo: { type: Boolean, default: true },
    showReviewStatus: { type: Boolean, default: true },
    showRemoveFilteredReports: { type: Boolean, default: true },
    showDiffType: { type: Boolean, default: true },
    reportCount: { type: Number, required: true },
    refreshFilter: { type: Boolean, default: false }
  },

  data() {
    return {
      activeBaselinePanelId: 0,
      activeCompareToPanelId: 0,
      activeDatePanelId: 0,
    };
  },

  computed: {
    ...mapState({
      reportFilter(state) {
        return state[this.namespace].reportFilter;
      },
      cmpData(state) {
        return state[this.namespace].cmpData;
      },
      console: () => console
    }),

  },

  watch: {
    refreshFilter(state) {
      if (!state) return;

      this.initByUrl();
      this.$emit("set-refresh-filter-state", false);
    }
  },

  mounted() {
    this.initByUrl();
  },

  beforeDestroy() {
    this.unregisterWatchers();

    const filters = this.$refs.filters;
    filters.forEach(filter => filter.unregisterWatchers());
  },

  methods: {
    beforeInit() {
      this.unregisterWatchers();
    },

    afterInit() {
      this.$emit("refresh");
      this.registerWatchers();
    },

    updateUrl() {
      const filters = this.$refs.filters;
      const states = filters.map(filter => filter.getUrlState());

      const queryParams = Object.assign({}, this.$route.query, ...states);
      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    registerWatchers() {
      this.unregisterWatchers();

      this.reportFilterUnwatch = this.$store.watch(
        state => state[this.namespace].reportFilter, () => {
          this.$emit("refresh");
        }, { deep: true });

      this.runIdsUnwatch = this.$store.watch(
        state => state[this.namespace].runIds, () => {
          this.$emit("refresh");
        });

      this.cmpDataUnwatch = this.$store.watch(
        state => state[this.namespace].cmpData, () => {
          this.$emit("refresh");
        }, { deep: true });
    },

    unregisterWatchers() {
      if (this.reportFilterUnwatch) this.reportFilterUnwatch();
      if (this.runIdsUnwatch) this.runIdsUnwatch();
      if (this.cmpDataUnwatch) this.cmpDataUnwatch();
    },

    initByUrl() {
      const filters = this.$refs.filters;

      // Before init.
      this.beforeInit();
      filters.forEach(filter => filter.beforeInit());

      // Init all filters by URL parameters.
      const results = filters.map(filter => {
        return filter.initByUrl();
      });

      // If all filters are initalized call a post function.
      Promise.all(results).then(() => {
        filters.forEach(filter => filter.afterInit());
        this.afterInit();

        // Close COMPARE TO expansion panel if no compare data is set.
        if (!this.cmpData?.runIds && !this.cmpData?.runTag &&
            !this.cmpData?.openReportsDate
        ) {
          this.activeCompareToPanelId = -1;
        }

        this.closePanelsOnInit();
      });
    },

    closePanelsOnInit() {
      // Close NEWCHECK expansion panel if no compare data is set.
      if (!this.cmpData?.runIds && !this.cmpData?.runTag) {
        this.activeNewcheckPanelId = -1;
      }

      // Close Dates expansion panel if no dates are set.
      if (!this.reportFilter.date) {
        this.activeDatePanelId = -1;
      }
    },

    saveCurrentFilter() {
      const preset = {
        id: 1,
        name: "BANANABREAD",
        reportFilter: this.reportFilter
      };

      new Promise(resolve => {
        ccService.getClient().storeFilterPreset(preset,
          handleThriftError(result => {
            resolve(result);
          })
        );
      })
      .then(result => {
        handleThriftError("OK", result);
      }).catch(err => {
        handleThriftError("FAILURE", err);
      });
    },

    deletePreset(preset_id){
      new Promise(resolve => {
        ccService.getClient().deleteFilterPreset(preset_id,
          handleThriftError(deleted_pr_id => {
            resolve(deleted_pr_id);
          })
        );
      })
        .then(deleted_pr_id => {
          handleThriftError("OK", deleted_pr_id);
        }).catch(err => {
          handleThriftError("FAILURE", err);
        });
    },

    async getFilterPreset(preset_id) {
      if (preset_id == null) {
        console.warn("getFilterPreset called without preset_id");
        return;
      }
      // const preset_id = 1;

      let filterPreset;
      try {
        filterPreset = await new Promise((resolve, reject) => {
          ccService.getClient().getFilterPreset(preset_id, (err, preset) => {
            if (err) return reject(err);
            resolve(preset);
          });
        });
      } catch (err) {
        console.error("FAILURE getFilterPreset failed:", err);
        return;
      }if (preset_id == null) {
    console.warn("getFilterPreset called without preset_id");
    return;
  }
      const rf = filterPreset?.reportFilter;
      if (!rf || typeof rf !== "object") return;

      const keyMap = {
        reviewStatus: "review-status",
        detectionStatus: "detection-status",
        diffType: "diff-type",
        severity: "severity",
        isUnique: "is-unique",
      };

      const getNameByValueForFilter = (rawKey, n) =>
        new Promise((resolve, reject) => {
          ccService.getClient().getNameByValueForFilter(rawKey, n, (err, name) => {
            if (err) return reject(err);
            resolve(name);
          });
        });

      const s = {};

      for (const [rawKey, rawValue] of Object.entries(rf)) {
        if (rawValue === null || rawValue === undefined || rawValue === "") continue;

        const urlKey = keyMap[rawKey] ?? rawKey;

        if (Array.isArray(rawValue)) {
          const convertedArr = await Promise.all(
            rawValue.map(async (v) => {
              if (v === null || v === undefined || v === "") return "";

              const n = Number(v);
              if (!Number.isInteger(n)) return String(v);

              try {
                const name = await getNameByValueForFilter(rawKey, n);
                return name !== "" ? String(name) : String(v);
              } catch (err) {
                console.warn(`Conversion failed for ${rawKey}=${v}:`, err);
                return String(v);
              }
            })
          );

          const cleaned = convertedArr.filter((x) => x !== "");
          if (cleaned.length > 0) s[urlKey] = cleaned;
          continue;
        }

        const n = Number(rawValue);
        if (Number.isInteger(n)) {
          try {
            const name = await getNameByValueForFilter(rawKey, n);
            s[urlKey] = name !== "" ? String(name) : String(rawValue);
          } catch (err) {
            console.warn(`Conversion failed for ${rawKey}=${rawValue}:`, err);
            s[urlKey] = String(rawValue);
          }
        } else {
          s[urlKey] = String(rawValue);
        }
      }

      const queryParams = { ...this.$route.query };
      for (const k of Object.values(keyMap)) delete queryParams[k];
      Object.assign(queryParams, s);

      await this.clearToolbarSilently();

      await this.$router.replace({ query: queryParams });
      await this.$nextTick(); // double check later if this funciton actually exists.
      await this.initByUrl();
    },

    async clearToolbarSilently() {
      const filters = this.$refs.filters;

      this.unregisterWatchers();
      filters.forEach(f => f.unregisterWatchers());

      await Promise.all(filters.map(f => f.clear(false)));

      this.updateAllFilters();
    },

    listFilterPreset(){
      new Promise(resolve => {
        ccService.getClient().listFilterPreset(
          handleThriftError(preset_list => {
            resolve(preset_list);
          })
        );
      })
        .then(preset_list => {
          handleThriftError("OK", preset_list);
        }).catch(err => {
          handleThriftError("FAILURE", err);
        });
      },

    async clearAllFilters() {
      const filters = this.$refs.filters;

      // Unregister watchers.
      this.unregisterWatchers();
      filters.forEach(filter => filter.unregisterWatchers());

      // Clear all filters and update the url.
      await Promise.all(filters.map(filter => filter.clear(false)));
      this.updateUrl();

      // Update filters after clear.
      this.updateAllFilters();

      // Register watchers.
      filters.forEach(filter => filter.registerWatchers());
      this.registerWatchers();
    },

    updateAllFilters() {
      const filters = this.$refs.filters;
      filters.forEach(filter => filter.update() );

      this.$emit("refresh");
    }
  }
};
</script>

<style lang="scss">
.v-expansion-panel--active > .v-expansion-panel-header,
.v-expansion-panel-header {
  min-height: 40px;
}

.v-expansion-panel-content > .v-expansion-panel-content__wrap {
  padding: 0 4px 0 6px;
}

#baseline-filters,
#compare-to-filters,
#date-filters {
  border: 1px solid rgba(0, 0, 0, 0.12);
}

#compare-to-filters {
  border-top: 0;
}

.v-expansion-panel-header__icon {
  order: 1;
}
.v-expansion-panel-header header {
  order: 2;
}
</style>
