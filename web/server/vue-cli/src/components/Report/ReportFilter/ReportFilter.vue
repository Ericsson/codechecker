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
          {{ tt }}
          {{ tt2 }}
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
// import PresetMenu from "./Filters/PresetMenu.vue";
// import { ReportFilter } from "@cc/report-server-types";
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
      tester: 0,
      tt: this.ReportFilter,
      tt2: JSON.parse(JSON.stringify(this.reportFilter))
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
      // const preset = reportFilter;
      // const preset = this.reportFilter;
      const preset = {
        id: 1,
        name: "BANANABREAD",
        reportFilter: this.reportFilter
      };

      localStorage.__tmp1 = JSON.stringify(Object.assign({}, ...this.$refs.filters.map(f => f.getUrlState())));

      this.tester = 1;

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
        this.tt = "promise";
        ccService.getClient().deleteFilterPreset(preset_id,
          handleThriftError(deleted_pr_id => {
            resolve(deleted_pr_id);
          })
        );
      })
        .then(deleted_pr_id => {
          this.tt = "OK" + deleted_pr_id;
          handleThriftError("OK", deleted_pr_id);
        }).catch(err => {
          this.tt = "FAILURE" + err;
          handleThriftError("FAILURE", err);
        });
    },

    // getFilterPreset(){
    //   // this.unregisterWatchers();
    //   // localStorage.__tmp1 = JSON.stringify(this.$route.query);
    //   // console.log(new URLSearchParams(JSON.parse(localStorage.__tmp1)).toString());

    //   // this.$router.replace({ query: { run: 'tinyxml', severity: 'Medium'} })

    //   // this.$router.replace({ query: JSON.parse(localStorage.__tmp1) })
    //   //   .then(() => {
    //   //     this.initByUrl();
    //   //   })
    //   //   .finally(() => {
    //   //     this.registerWatchers();
    //   //   });
    //   // console.log();

    //   const preset_id = 1;
    //   // console.log(this.ReportFilter);
    //   new Promise(resolve => {
    //     ccService.getClient().getFilterPreset(preset_id,
    //       handleThriftError(Filter_Preset => {
    //         resolve(Filter_Preset);
    //       })
    //     );
    //   })
    //     .then(Filter_Preset => {
    //       console.log(Filter_Preset.reportFilter);
    //       this.setReportFilter(
    //         new ReportFilter(Filter_Preset.reportFilter));
    //       // this.updateReportFilter();
    //       // this.unregisterWatchers();
    //       // this.registerWatchers();
    //       // this.$emit("refresh");
    //       // this.update();

    //     }).catch(err => {
    //       handleThriftError("FAILURE", err);
    //     });
    // },
    getFilterPreset() {
      const preset_id = 1;
      // console.log(this.ReportFilter);
      new Promise(resolve => {
        ccService.getClient().getFilterPreset(preset_id,
          handleThriftError(Filter_Preset => {
            resolve(Filter_Preset);
          })
        );
      })
        .then(Filter_Preset => {
          // this.unregisterWatchers();
          // this.setReportFilter(JSON.parse(
          //   JSON.stringify(Filter_Preset.reportFilter)), { replace: true });
          this.console.log(" Before this.reportFilter,", this.reportFilter)
          this.setReportFilter(Filter_Preset.reportFilter);
          this.updateUrl();
          // work around 1 using saved states to combine with current and avoid updating url manually.
          try {
            console.log(" Before this.reportFilter,", this.reportFilter, Filter_Preset);
            // this.beforeInit();
            const s = JSON.parse(localStorage.__tmp1 ?? "{}");
            const queryParams = Object.assign({}, this.$route.query, s);
            console.log('queryParams', queryParams);
            this.$router.replace({ query: queryParams }).then(() => {
              this.initByUrl();
            }).catch(console.error);
          } catch (e) {
            console.error('error in try-catch clause', e);
          }
          console.log("After this.reportFilter,", this.reportFilter);
        }).catch(err => {
          handleThriftError("FAILURE", err);
        });
    },

  listFilterPreset(){
      new Promise(resolve => {
        this.tt = "promise";
        ccService.getClient().listFilterPreset(
          handleThriftError(preset_list => {
            resolve(preset_list);
          })
        );
      })
        .then(preset_list => {
          this.tt = "OK" + preset_list;
          handleThriftError("OK", preset_list);
        }).catch(err => {
          this.tt = "FAILURE" + err;
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
