<template>
  <v-dialog
    v-model="savePresetDialogOpen"
    max-width="420"
  >
    <v-card>
      <v-card-title>
        {{ saveDialogTitle }}
      </v-card-title>

      <v-card-text>
        <v-text-field
          v-model="presetName"
          label="Preset name"
          autofocus
          variant="outlined"
          clearable
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          @click="savePresetDialogOpen = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          :disabled="!presetName"
          @click="savePreset(saveMode)"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
  <div>
    <div
      class="mt-2 mb-2 d-flex align-center justify-space-between w-100 p-1"
    >
      <ClearAllFilters
        :namespace="namespace"
        @clear="clearAllFilters"
      />
      <ReportCount :value="reportCount" />
    </div>

    <v-divider />

    <!-- PresetMenu component -->
    <v-list-item class="pl-1">
      <span
        class="
          text-body-2
          font-weight-semibold
          mr-2
          text-truncate"
      >
        Filter Preset
      </span>
      <tooltip-help-icon
        class="mr-2"
      >
        <b>Filter Presets</b> enables saving and reloading predefined report
        filter configurations.
        <br>
        <ul>
          <li>
            <b>Create preset</b>: Creates a new preset based on the
            current report filter configuration.
          </li>
          <li>
            <b>Override preset</b>: Overrides the currently selected preset
            with the modified report filter configuration.
          </li>
          <li>
            <b>Create as new</b>: Saves the current report filter configuration
            as a new filter preset.
          </li>
        </ul>
        <br>
        <i>Note: Overriding and creating as new are available if a filter
          preset is selected and the report filter configuration is
          modified.
        </i>
      </tooltip-help-icon>
      <preset-menu
        ref="presetMenuRef"
        @apply-preset="initFilterPresetFromUrl"
        @clear-preset="clearAllFilters"
      />

      <div
        v-if="canSeeActions && !presetMenuRef?.isModified
          && !presetMenuRef?.activePresetId"
        class="d-flex flex-column mb-2 mt-2"
      >
        <v-btn
          color="primary"
          @click="createPresetDialog"
        >
          Create Preset
        </v-btn>
      </div>
      <div
        v-if="canSeeActions && !presetMenuRef?.isModified
          && presetMenuRef?.activePresetId"
        class="d-flex flex-column mb-2 mt-2"
      >
        <v-btn
          color="primary"
          class="mb-2"
          @click="renamePresetDialog"
        >
          Rename
        </v-btn>
      </div>
      <div
        v-if="canSeeActions && presetMenuRef?.isModified"
        class="d-flex flex-column mb-2 mt-2"
      >
        <v-btn
          color="primary"
          class="mb-2"
          @click="overridePresetDialog"
        >
          Override Preset
        </v-btn>
        <v-btn
          color="primary"
          @click="createPresetAsNewDialog"
        >
          Create as new
        </v-btn>
      </div>
    </v-list-item>

    <v-divider />

    <div>
      <unique-filter
        :ref="setFilterRef"
        :namespace="namespace"
        @update:url="updateUrl"
      />
    </div>

    <v-divider />

    <v-list
      density="compact"
      :border="false"
      :rounded="false"
      elevation="0"
    >
      <v-list-item class="pl-0 border-sm border-solid border-opacity">
        <v-expansion-panels
          v-model="activeBaselinePanelId"
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0"
              hide-actions
            >
              <template #default="{ expanded }">
                <v-icon class="expansion-btn">
                  {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
                </v-icon>
                <span
                  class="
                    text-body-2
                    font-weight-semibold
                    mr-2
                    text-truncate"
                ><b>BASELINE</b></span>
                <v-spacer />
              </template>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <baseline-run-filter
                :ref="setBaselineRunFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider />

              <baseline-open-reports-date-filter
                :ref="setBaselineOpenReportsDateFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item
        v-if="showCompareTo"
        class="pl-0 border-sm border-solid border-opacity border-t-0"
      >
        <v-expansion-panels
          v-model="activeCompareToPanelId"
          hover
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0"
              hide-actions
            >
              <template #default="{ expanded }">
                <v-icon class="expansion-btn">
                  {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
                </v-icon>
                <span
                  class="
                    text-body-2
                    font-weight-semibold
                    mr-2
                    text-truncate"
                ><b>COMPARE TO</b></span>
                <v-spacer />
              </template>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <compared-to-run-filter
                :ref="setComparedToRunFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider />

              <compared-to-open-reports-date-filter
                :ref="setComparedToOpenReportsDateFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider v-if="showDiffType" />

              <compared-to-diff-type-filter
                v-if="showDiffType"
                :ref="setComparedToDiffTypeFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item class="pl-1">
        <file-path-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <checker-name-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <severity-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <report-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider v-if="showReviewStatus" />

      <v-list-item
        v-if="showReviewStatus"
        class="pl-1"
      >
        <review-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <detection-status-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <analyzer-name-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <source-component-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <cleanup-plan-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <checker-message-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-list-item class="pl-0 border-sm border-solid border-opacity">
        <v-expansion-panels
          v-model="activeDatePanelId"
          hover
          eager
        >
          <v-expansion-panel>
            <v-expansion-panel-title
              class="pa-0"
              hide-actions
            >
              <template #default="{ expanded }">
                <v-icon class="expansion-btn">
                  {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
                </v-icon>
                <span
                  class="
                    text-body-2
                    font-weight-semibold
                    mr-2
                    text-truncate"
                ><b>Dates</b></span>
                <v-spacer />
              </template>
            </v-expansion-panel-title>
            <v-expansion-panel-text class="pa-1">
              <detection-date-filter
                id="detection-date-filter"
                :ref="setDetectionDateFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />

              <v-divider class="mt-2" />

              <fix-date-filter
                id="fix-date-filter"
                :ref="setFixDateFilterRef"
                :namespace="namespace"
                @update:url="updateUrl"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list-item>

      <v-list-item class="pl-1">
        <report-hash-filter
          id="report-hash-filter"
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <bug-path-length-filter
          id="bug-path-length-filter"
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>

      <v-divider />

      <v-list-item class="pl-1">
        <testcase-filter
          :ref="setFilterRef"
          :namespace="namespace"
          @update:url="updateUrl"
        />
      </v-list-item>
    </v-list>

    <v-divider v-if="showRemoveFilteredReports" />

    <div
      v-if="showRemoveFilteredReports"
      class="mt-2 mb-2 d-flex align-center justify-center w-100 p-1"
    >
      <remove-filtered-reports
        class="mt-4 w-100"
        :namespace="namespace"
        @update="updateAllFilters"
      />
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  toRef,
  watch
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStore } from "vuex";

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

import { useBaseFilter } from "@/composables/useBaseFilter";

import ClearAllFilters from "./ClearAllFilters";
import RemoveFilteredReports from "./RemoveFilteredReports";
import ReportCount from "./ReportCount";
import PresetMenu from "./Filters/PresetMenu.vue";
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import {
  authService,
  ccService,
  handleThriftError,
  prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";

const props = defineProps({
  namespace: { type: String, required: true },
  showCompareTo: { type: Boolean, default: true },
  showReviewStatus: { type: Boolean, default: true },
  showRemoveFilteredReports: { type: Boolean, default: true },
  showDiffType: { type: Boolean, default: true },
  reportCount: { type: Number, required: true },
  refreshFilter: { type: Boolean, default: false }
});

const emit = defineEmits([ "set-refresh-filter-state", "refresh" ]);

const activeBaselinePanelId = ref(undefined);
const baselineRunFilterRef = ref(null);
const setBaselineRunFilterRef = el => {
  baselineRunFilterRef.value = el;
  setFilterRef(el);
};
const baselineOpenReportsDateFilterRef = ref(null);
const setBaselineOpenReportsDateFilterRef = el => {
  baselineOpenReportsDateFilterRef.value = el;
  setFilterRef(el);
};

const activeCompareToPanelId = ref(undefined);
const comparedToRunFilterRef = ref(null);
const setComparedToRunFilterRef = el => {
  comparedToRunFilterRef.value = el;
  setFilterRef(el);
};

const comparedToOpenReportsDateFilterRef = ref(null);
const setComparedToOpenReportsDateFilterRef = el => {
  comparedToOpenReportsDateFilterRef.value = el;
  setFilterRef(el);
};

const comparedToDiffTypeFilterRef = ref(null);
const setComparedToDiffTypeFilterRef = el => {
  comparedToDiffTypeFilterRef.value = el;
  setFilterRef(el);
};

const activeDatePanelId = ref(undefined);
const detectionDateFilterRef = ref(null);
const setDetectionDateFilterRef = el => {
  detectionDateFilterRef.value = el;
  setFilterRef(el);
};

const fixDateFilterRef = ref(null);
const setFixDateFilterRef = el => {
  fixDateFilterRef.value = el;
  setFilterRef(el);
};

const filters = ref([]);
const isInitializing = ref(false);
const savePresetDialogOpen = ref(false);
const saveMode = ref("create");
const presetName = ref("");
const isSuperUser = ref(false);
const isAdminOfAnyProduct = ref(false);
const presetMenuRef = ref(null);

const setFilterRef = el => {
  if (el && !filters.value.includes(el)) {
    filters.value.push(el);
  }
};

const {
  reportFilterUnwatch,
  runIdsUnwatch,
  cmpDataUnwatch
} = useBaseFilter(toRef(props, "namespace"));

const route = useRoute();
const router = useRouter();
const store = useStore();

const reportFilter = computed(() => store.state[props.namespace].reportFilter);
const canSeeActions = computed(() => {
  return isSuperUser.value || isAdminOfAnyProduct.value;
});
const saveDialogTitle = computed(() => {
  const titles = {
    create: "Create new preset",
    override: "Override existing preset",
    createNew: "Save as new preset",
    rename: "Rename the preset"
  };
  return titles[saveMode.value] || "Save filter preset";
});

watch(() => props.refreshFilter, state => {
  if (!state) return;

  initByUrl();
  emit("set-refresh-filter-state", false);
});

onMounted(() => {
  nextTick(() => {
    initByUrl();
  });

  authService.getClient().hasPermission(
    Permission.SUPERUSER,
    "",
    handleThriftError(_isSuperUser => {
      isSuperUser.value = _isSuperUser;

      if (!isSuperUser.value) {
        prodService.getClient().isAdministratorOfAnyProduct(
          handleThriftError(_isAdminOfAnyProduct => {
            isAdminOfAnyProduct.value = _isAdminOfAnyProduct;
          })
        );
      }
    })
  );
});

function beforeInit() {
  unregisterWatchers();
}

function afterInit() {
  emit("refresh");
  registerWatchers();
  syncGroupPanels();
}

function updateUrl() {
  syncGroupPanels();
  const _filters = filters.value;

  if (!_filters?.length) {
    return;
  };

  const _states = _filters
    .filter(filter => filter?.getUrlState)
    .map(filter => filter?.getUrlState?.());

  const _queryParams = Object.assign({}, route.query, ..._states);
  router.replace({ query: _queryParams }).catch(() => {});
}

function registerWatchers() {
  unregisterWatchers();

  reportFilterUnwatch.value = store.watch(
    state => state[props.namespace].reportFilter, () => {
      emit("refresh");
    }, { deep: true });

  runIdsUnwatch.value = store.watch(
    state => state[props.namespace].runIds, () => {
      emit("refresh");
    });

  cmpDataUnwatch.value = store.watch(
    state => state[props.namespace].cmpData, () => {
      emit("refresh");
    }, { deep: true });
}

function unregisterWatchers() {
  if (reportFilterUnwatch.value) reportFilterUnwatch.value();
  if (runIdsUnwatch.value) runIdsUnwatch.value();
  if (cmpDataUnwatch.value) cmpDataUnwatch.value();
}

async function initByUrl() {
  if (isInitializing.value) return;
  isInitializing.value = true;

  const _filters = filters.value;
  if (!_filters?.length) {
    isInitializing.value = false;
    return;
  };

  // Before init.
  beforeInit();
  _filters.forEach(filter => {
    if (filter?.beforeInit) filter?.beforeInit?.();
  });

  const presetId = route.query.filterPreset;

  if (presetId && presetMenuRef.value) {
    await presetMenuRef.value.fetchPresets();
    await presetMenuRef.value.selectPresetSilently(Number(presetId));
    const presetSnapshot = await buildPresetQuery(presetId);
    if (presetSnapshot) {
      presetMenuRef.value.onPresetApplied(presetSnapshot);
    }
  }

  // Init all filters by URL parameters.
  const _results = _filters
    .filter(filter => filter?.initByUrl)
    .map(filter => filter?.initByUrl?.());

  // If all filters are initalized call a post function.
  Promise.all(_results).then(() => {
    _filters.forEach(filter => {
      if (filter?.afterInit) filter?.afterInit?.();
    });
    afterInit();
  }).finally(() => {
    isInitializing.value = false;
  });

}

async function clearAllFilters() {
  const _filters = filters.value;
  if (!_filters?.length) return;

  presetMenuRef.value.clearPresetState();

  // Unregister watchers.
  unregisterWatchers();
  _filters.forEach(filter => filter?.unregisterWatchers?.());

  // Clear all filters and update the url.
  await Promise.all(_filters.map(filter => filter?.clear?.(false)));

  // Clear FilterPreset from url.
  await router.replace({ query: { ...route.query,
    filterPreset: undefined } }).catch(() => {});

  updateUrl();

  // Update filters after clear.
  updateAllFilters();

  // Register watchers.
  _filters.forEach(filter => filter?.registerWatchers?.());
  registerWatchers();
}

function updateAllFilters() {
  const _filters = filters.value;
  if (!_filters?.length) return;

  _filters.forEach(filter => filter?.update?.() );

  emit("refresh");
}

onBeforeUnmount(() => {
  unregisterWatchers();

  const _filters = filters.value;
  if (_filters?.length) {
    _filters.forEach(filter => filter?.unregisterWatchers?.());
  }
});

async function savePreset(mode) {
  try {
    let result;

    // Store selected run names in reportFilter.runName (not part of the
    // standard filter state, but needed for preset serialization).
    const presetReportFilter = structuredClone(reportFilter.value);
    const runFilter = filters.value.find(f => f.id === "run");
    presetReportFilter.runName = runFilter?.selectedItems?.map(i => i.id) ?? [];

    const activePresetId = presetMenuRef.value?.activePresetId;
    if (mode === "rename") {
      const new_name = presetName.value;
      result = await new Promise(resolve => {
        ccService.getClient().renameFilterPreset(activePresetId, new_name,
          handleThriftError(result => {
            resolve(result);
          })
        );
      });
    } else {
      const preset = {
        id: mode === "override" && activePresetId
          ? activePresetId
          : -1,
        name: presetName.value,
        reportFilter: presetReportFilter
      };

      result = await new Promise(resolve => {
        ccService.getClient().storeFilterPreset(preset,
          handleThriftError(result => {
            resolve(result);
          })
        );
      });
    }

    savePresetDialogOpen.value = false;
    presetName.value = "";
    presetMenuRef.value?.selectPresetAfterSave(result);
  } catch (err) {
    handleThriftError("Failed to save a preset: ", err);
  }
}

function overridePresetDialog() {
  saveMode.value = "override";
  savePresetDialogOpen.value = true;
  presetName.value = presetMenuRef.value.activePresetName;
}

function createPresetAsNewDialog() {
  saveMode.value = "createNew";
  savePresetDialogOpen.value = true;
  presetName.value = presetMenuRef.value.activePresetName;
}

function createPresetDialog() {
  saveMode.value = "create";
  savePresetDialogOpen.value = true;
  presetName.value = presetMenuRef.value.activePresetName;
}

function renamePresetDialog() {
  saveMode.value = "rename";
  savePresetDialogOpen.value = true;
  presetName.value = presetMenuRef.value.activePresetName;
}

function syncGroupPanels() {
  activeBaselinePanelId.value =
    baselineRunFilterRef.value.panel ||
    baselineOpenReportsDateFilterRef.value.panel ? 0 : undefined;

  activeCompareToPanelId.value =
    comparedToRunFilterRef.value.panel ||
    comparedToOpenReportsDateFilterRef.value.panel ||
    comparedToDiffTypeFilterRef.value.panel ? 0 : undefined;

  activeDatePanelId.value =
    detectionDateFilterRef.value.panel ||
    fixDateFilterRef.value.panel ? 0 : undefined;
  console.error("detectionDateFilterRef=", detectionDateFilterRef.value.panel);
  console.error("fixDateFilterRef=", fixDateFilterRef.value.panel);
  console.error("activeDatePanelId=", activeDatePanelId.value);
}
/*function deletePreset(preset_id) {
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
        }*/

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

  if (Array.isArray(value)) {
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
    [ "run", rawValue || "" ],
  ],
  runTag: (_, rawValue) => [ //PTR
    [ "run-tag", rawValue || "" ],
  ],
  componentNames: (_, rawValue) =>
    asArray(rawValue).map(v => [ "source-component", v ]),

  diffType: (_, rawValue) => [
    [ "diff-type",
      toTitleCase(toEnumNames(rawValue, ENUMS_FOR_STATUSES.diffType)) ],
  ],
  bugPathLength: (_, rawValue) => {
    const toStr = v => (v != null && typeof v.toNumber === "function")
      ? String(v.toNumber()) : (v != null ? String(v) : "");
    return [
      [ "min-bug-path-length", toStr(rawValue?.min) ],
      [ "max-bug-path-length", toStr(rawValue?.max) ],
    ];
  },
  date: (_, rawValue) => [
    [ "detected-after", toISO(rawValue?.detected?.after) ],
    [ "detected-before", toISO(rawValue?.detected?.before) ],
    [ "fixed-after", toISO(rawValue?.fixed?.after) ],
    [ "fixed-before", toISO(rawValue?.fixed?.before) ],
  ],
  analyzerNames: (_, rawValue) =>
    asArray(rawValue).map(v => [ "analyzer-name", v ]),
  openReportsDate: (_, rawValue) => [
    [ "open-reports-date", toISO(rawValue) || "" ],
  ],
  cleanupPlanNames: (_, rawValue) =>
    asArray(rawValue).map(v => [ "cleanup-plan", v ]),
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
  fullReportPathInComponent: (_, rawValue) => {
    if (!rawValue) return [];
    return [ [ "sameorigin-sourcecomponent", "true" ] ];
  },

};

async function buildPresetQuery(presetId) {
  let filterPreset;
  try {
    filterPreset = await new Promise((resolve, reject) => {
      ccService.getClient().getFilterPreset(presetId, (err, preset) => {
        if (err) return reject(err);
        resolve(preset);
      });
    });
  } catch {
    return null;
  }

  const rf = filterPreset?.reportFilter;
  if (!rf || typeof rf !== "object") return null;

  const presetQueryParams = {};
  for (const [ rawKey, rawValue ] of Object.entries(rf)) {
    if (rawValue === null || rawValue === undefined || rawValue === "") {
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
  return { ...presetQueryParams, filterPreset: presetId };
}

async function initFilterPreset(presetId) {
  if (presetId == null) {
    console.warn("getFilterPreset called without presetId");
    return;
  }

  let filterPreset;
  try {
    filterPreset = await new Promise((resolve, reject) => {
      ccService.getClient().getFilterPreset(presetId, (err, preset) => {
        if (err) return reject(err);
        resolve(preset);
      });
    });
  } catch (err) {
    handleThriftError("Failed to initialize a preset: ", err);
    return;
  }

  const rf = filterPreset?.reportFilter;

  if (!rf || typeof rf !== "object") return;

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

  clearToolbarSilently();

  const nextQuery = { ...presetQueryParams, filterPreset: presetId };
  await router.replace({ query: nextQuery }).catch(() => {});

  if (presetMenuRef.value) {
    presetMenuRef.value.onPresetApplied({ ...route.query });
  }
}

async function initFilterPresetFromUrl(presetId){
  // replace query parameters with preset parameters.
  await initFilterPreset(presetId);
  await initByUrl();
  updateUrl();
  await nextTick();
}

async function clearToolbarSilently() {
  const _filters = filters.value;
  unregisterWatchers();
  _filters.forEach(f => f.unregisterWatchers());
  await Promise.all(_filters.map(f => f.clear(false)));
}

/*function listFilterPreset() {
  new Promise(
    resolve => {
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
}*/
</script>

<style lang="scss">
.v-list-item {
  min-height: 40px !important;
  padding-top: 2px !important;
  padding-bottom: 2px !important;
}

.v-expansion-panel--active > .v-expansion-panel-title,
.v-expansion-panel-title {
  min-height: 40px !important;
  font-size: 0.875rem !important;
}

.v-expansion-panel-text > .v-expansion-panel-text__wrapper {
  padding: 0 4px 0 6px !important;
}

#baseline-filters,
#compare-to-filters,
#date-filters {
  border: 1px solid rgba(0, 0, 0, 0.12);
}

#compare-to-filters {
  border-top: 0;
}

.v-expansion-panel-title__icon {
  order: 1;
}
.v-expansion-panel-title header {
  order: 2;
}
</style>
