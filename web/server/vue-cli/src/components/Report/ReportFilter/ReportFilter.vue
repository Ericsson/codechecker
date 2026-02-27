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

      <!-- PresetMenu component -->
      <v-list-item class="pl-1">
        <v-list-item-content>
          <preset-menu
            ref="FilterMenu"
            @apply-preset="getFilterPreset"
            @clear-preset="clearAllFilters"
          />
        </v-list-item-content>

        <v-btn
          v-if="canSeeActions"
          class="ml-4"
          color="primary"
          @click="open_preset_save = true"
        >
          Save preset
        </v-btn>
        <v-dialog v-model="open_preset_save" max-width="420">
          <v-card>
            <v-card-title>
              Save filter preset
            </v-card-title>

            <v-card-text>
              <v-text-field
                v-model="presetName"
                label="Preset name"
                autofocus
                outlined
                clearable
              />
            </v-card-text>

            <v-card-actions>
              <v-spacer />

              <v-btn text @click="open_preset_save = false">
                Cancel
              </v-btn>

              <v-btn
                color="primary"
                :disabled="!presetName"
                @click="saveCurrentFilter"
              >
                Save
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
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
import PresetMenu from "./Filters/PresetMenu.vue";
import {
  authService,
  ccService,
  handleThriftError,
  prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";

export default {
  name: "ReportFilter",
  components: {
    AnalyzerNameFilter,
    PresetMenu,
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
      open_preset_save: false,
      presetName: "",
      isSuperUser: false,
      isAdminOfAnyProduct: false,
    };
  },

  computed: {
    ...mapState({
      reportFilter(state) {
        return state[this.namespace].reportFilter;
      },
      cmpData(state) {
        return state[this.namespace].cmpData;
      }
    }),
    canSeeActions() {
      return this.isSuperUser || this.isAdminOfAnyProduct;
    }
  },

  watch: {
    refreshFilter(state) {
      if (!state) return;

      this.initByUrl();
      this.$emit("set-refresh-filter-state", false);
    }
  },

  created() {
    authService.getClient().hasPermission(
      Permission.SUPERUSER,
      "",
      handleThriftError(isSuperUser => {
        this.isSuperUser = isSuperUser;

        if (!isSuperUser) {
          prodService.getClient().isAdministratorOfAnyProduct(
            handleThriftError(isAdmin => {
              this.isAdminOfAnyProduct = isAdmin;
            })
          );
        }
      })
    );
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
      return Promise.all(results).then(() => {
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
        name: this.presetName,
        reportFilter: this.reportFilter
      };
      new Promise(resolve => {
        ccService.getClient().storeFilterPreset(preset,
          handleThriftError(result => {
            resolve(result);
          })
        );
        this.open_preset_save = false;
        this.presetName = "";
      })
        .then(result => {
          handleThriftError("OK", result);
        }).catch(err => {
          handleThriftError("FAILURE", err);
        });
    },
    deletePreset(preset_id) {
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
      let filterPreset;
      try {
        filterPreset = await new Promise((resolve, reject) => {
          ccService.getClient().getFilterPreset(preset_id, (err, preset) => {
            if (err) return reject(err);
            resolve(preset);
          });
        });
      } catch (err) {
        handleThriftError("getFilterPreset failed:", err);
        return;
      }

      if (preset_id == null) {
        handleThriftError("getFilterPreset called without preset_id");
        return;
      }

      // helper functions
      function toTitleCase(word) {
        if (word == null) return "";
        return String(word)
          .toLowerCase()
          .replace(/^\w/, c => c.toUpperCase());
      }
      function toEnumNames(value, map) {
        const normalizeOne = v => {
          if (v === null || v === undefined || v === "") return "";
          const n = typeof v === "string" &&
          v.trim() !== "" ? Number(v) : v;
          return map?.[n] ?? map?.[v] ?? String(v);
        };

        if (Array.isArray(value)){
          return value.map(normalizeOne).filter(Boolean);
        }
        return normalizeOne(value);
      }
      const toISO = sec => {
        if (!sec) return "";
        const d = new Date(sec * 1000);
        return isNaN(d.getTime()) ? "" : d.toISOString();
      };
      const asArray = v => (Array.isArray(v) ? v : (v == null ? [] : [ v ]));

      const ENUMS_FOR_STATUSES = {
        detectionStatus: {
          0: "NEW",
          1: "RESOLVED",
          2: "UNRESOLVED",
          3: "REOPENED",
          4: "OFF",
          5: "UNAVAILABLE",
        },
        diffType: {
          0: "NEW",
          1: "RESOLVED",
          2: "UNRESOLVED",
        },
        reviewStatus: {
          0: "UNREVIEWED",
          1: "CONFIRMED BUG", // Confirmed -> Confirmed bug
          2: "FALSE POSITIVE", // False_positive -> False positive
          3: "INTENTIONAL",
        },
        severity: {
          0: "UNSPECIFIED",
          10: "STYLE",
          20: "LOW",
          30: "MEDIUM",
          40: "HIGH",
          50: "CRITICAL",
        },
        order: {
          0: "ASC",
          1: "DESC",
        },
        reportStatus: {
          0: "OUTSTANDING",
          1: "CLOSED",
        }
      };

      const rf = filterPreset?.reportFilter;

      if (!rf || typeof rf !== "object") return;

      const FilterToQuery = {
        filepath: (_, rawValue) =>
          asArray(rawValue).map(v => [ "filepath", v ]),
        checkerMsg: (_, rawValue) =>
          asArray(rawValue).map(v => [ "checker-msg", v ]),
        checkerName: (_, rawValue) =>
          asArray(rawValue).map(v => [ "checker-name", v ]),
        reportHash: (_, rawValue) =>
          asArray(rawValue).map(v => [ "report-hash", v ]),
        severity: (_, rawValue) => {
          const values = Array.isArray(rawValue) ? rawValue : [ rawValue ];
          return values
            .map(v => [
              "severity",
              toTitleCase(toEnumNames(v, ENUMS_FOR_STATUSES.severity))
            ])
            .filter(([ , val ]) => val !== "");
        },
        reviewStatus: (_, rawValue) => {
          const values = Array.isArray(rawValue) ? rawValue : [ rawValue ];
          return values
            .map(v => [
              "review-status",
              toTitleCase(toEnumNames(v, ENUMS_FOR_STATUSES.reviewStatus))
            ])
            .filter(([ , val ]) => val !== "");
        },
        detectionStatus: (_, rawValue) => {
          const values = Array.isArray(rawValue) ? rawValue : [ rawValue ];
          return values
            .map(v => [ "detection-status",
              toTitleCase(toEnumNames(v, ENUMS_FOR_STATUSES.detectionStatus)) ])
            .filter(([ , val ]) => val !== "");
        },
        runHistoryTag: (_, rawValue) => [ // PTR
          asArray(rawValue).map(v => [ "run-history-tag", v ]),
        ],
        firstDetectionDate: (_, rawValue) => [ //PTR
          [ "first-detection-date", rawValue || "" ],
        ],
        fixDate: (_, rawValue) => [
          [ "fixed-after", toISO(rawValue?.after) || "" ],
          [ "fixed-before", toISO(rawValue?.before) || "" ],
        ],
        isUnique: (_, rawValue) => [
          [ "is-unique", rawValue ? "on" : "off" ],
        ],
        runName: (_, rawValue) => [ //PTR
          [ "run-name", rawValue || "" ],
        ],
        runTag: (_, rawValue) => [ //PTR
          [ "run", rawValue || "" ],
        ],
        componentNames: (_, rawValue) =>
          asArray(rawValue).map(v => [ "source-component", v ]),

        diffType: (_, rawValue) => [
          [ "diff-type",
            toTitleCase(toEnumNames(rawValue, ENUMS_FOR_STATUSES.diffType)) ],
        ],
        bugPathLength: (_, rawValue) => [
          [ "min-bug-path-length", rawValue?.min ?? rawValue?.from ?? "" ],
          [ "max-bug-path-length", rawValue?.max ?? rawValue?.to ?? "" ],
        ],
        date: (_, rawValue) => [
          [ "detected-after",  toISO(rawValue?.detected?.after) ],
          [ "detected-before", toISO(rawValue?.detected?.before) ],
          [ "fixed-after",     toISO(rawValue?.fixed?.after) ],
          [ "fixed-before",    toISO(rawValue?.fixed?.before) ],
        ],
        analyzerNames: (_, rawValue) =>
          asArray(rawValue).map(v => [ "analyzer-name", v ]),
        openReportsDate: (_, rawValue) => [
          [ "open-reports-date", toISO(rawValue) || "" ],
        ],
        cleanupPlanNames: (_, rawValue) =>
          asArray(rawValue).map(v => [ "cleanup-plan-name", v ]),
        fileMatchesAnyPoint: (_, rawValue) => {
          if (!rawValue) return [];
          return [ [ "anywhere-filepath", "true" ] ];
        },
        componentMatchesAnyPoint: (_, rawValue) => {
          if (!rawValue) return [];
          return [ [ "anywhere-sourcecomponent", "true" ] ];
        },
        annotations: (_, rawValue) => {
          const testcases = Array.isArray(rawValue)
            ? rawValue
              .filter(a => a.first === "testcase")
              .map(a => a.second)
            : rawValue.first === "testcase"
              ? [ rawValue.second ]
              : [];
          return testcases.map(tc => [ "testcase", tc ]);
        },
        reportStatus: (_, rawValue) => {
          const values = asArray(rawValue);
          return values
            .map(v => [ "report-status",
              toTitleCase(toEnumNames(v, ENUMS_FOR_STATUSES.reportStatus)) ])
            .filter(([ , val ]) => val !== "");
        },
        fullReportPathInComponent: (_, rawValue) => [
          [ "sameorigin-sourcecomponent", rawValue ? "true" : "false" ],
        ],

      };

      const presetQueryParams = {};

      for (const [ rawKey, rawValue ] of Object.entries(rf)) {
        if (rawValue === null || rawValue === undefined || rawValue === ""){
          continue;
        }

        const mapper = FilterToQuery[rawKey];

        if (typeof mapper === "string") {
          presetQueryParams[mapper] = rawValue;
          continue;
        }

        if (typeof mapper === "function") {
          const pairs = mapper(rf, rawValue);

          for (const [ k, v ] of pairs) {
            if (v === null || v === undefined || v === "") continue;

            if (k in presetQueryParams) {
              const prev = Array.isArray(presetQueryParams[ k ]) ?
                presetQueryParams[ k ] : [ presetQueryParams[ k ] ];
              const next = Array.isArray(v) ? v : [ v ];
              presetQueryParams[ k ] = [ ...prev, ...next ];
            } else {
              presetQueryParams[ k ] = v;
            }
          }
          continue;
        }

        presetQueryParams[ rawKey ] = rawValue;
      }

      await this.clearToolbarSilently();

      await new Promise(resolve => setTimeout(resolve, 100));

      const nextQuery = { ...presetQueryParams };
      await this.$router.replace({ query: nextQuery }).catch(() => {});

      await this.initByUrl();

      const filters = this.$refs.filters;
      const states = filters.map(f => f.getUrlState());
      const settledQuery = Object.assign({}, this.$route.query, ...states);

      this.updateUrl();

      if (this.$refs.FilterMenu && this.$refs.FilterMenu[0]) {
        this.$refs.FilterMenu[0].onPresetApplied(settledQuery);
      }
    },

    async clearToolbarSilently() {
      const filters = this.$refs.filters;
      this.unregisterWatchers();
      filters.forEach(f => f.unregisterWatchers());
      await Promise.all(filters.map(f => f.clear(false)));
      this.updateAllFilters();
    },

    listFilterPreset() {
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

      if (this.$refs.FilterMenu && this.$refs.FilterMenu[0]) {
        this.$refs.FilterMenu[0].clearPresetState();
      }

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
