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
        <v-list-item-action class="mr-5">
          <clear-all-filters
            :namespace="namespace"
            @clear="clearAllFilters"
          />
        </v-list-item-action>

        <v-spacer />

        <report-count
          :value="reportCount"
        />
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

      <v-list-item id="baseline-filters" class="pl-1">
        <v-list-item-content class="pa-0">
          <v-expansion-panels
            v-model="activeBaselinePanelId"
            hover
          >
            <v-expansion-panel>
              <v-expansion-panel-header
                class="pa-0 px-1 primary--text"
              >
                <b>BASELINE</b>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="pa-1">
                <baseline-run-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
                <baseline-tag-filter
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
        v-if="showNewcheck"
        id="newcheck-filters"
        class="pl-1"
      >
        <v-list-item-content class="pa-0">
          <v-expansion-panels
            v-model="activeNewcheckPanelId"
            hover
          >
            <v-expansion-panel>
              <v-expansion-panel-header
                class="pa-0 px-1 primary--text"
              >
                <b>NEWCHECK</b>
              </v-expansion-panel-header>
              <v-expansion-panel-content class="pa-1">
                <newcheck-run-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
                <newcheck-tag-filter
                  ref="filters"
                  :namespace="namespace"
                  @update:url="updateUrl"
                />
                <newcheck-diff-type-filter
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

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <checker-name-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <severity-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

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

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <detection-status-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <source-component-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <checker-message-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <detection-date-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <report-hash-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item class="pl-1">
        <v-list-item-content class="pa-0">
          <bug-path-length-filter
            ref="filters"
            :namespace="namespace"
            @update:url="updateUrl"
          />
        </v-list-item-content>
      </v-list-item>

      <v-list-item
        v-if="showRemoveFilteredReports"
        class="pl-1"
      >
        <v-list-item-content>
          <remove-filtered-reports
            class="mt-4"
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
  BaselineRunFilter,
  BaselineTagFilter,
  BugPathLengthFilter,
  CheckerMessageFilter,
  CheckerNameFilter,
  DetectionDateFilter,
  DetectionStatusFilter,
  FilePathFilter,
  NewcheckDiffTypeFilter,
  NewcheckRunFilter,
  NewcheckTagFilter,
  ReportHashFilter,
  ReviewStatusFilter,
  SeverityFilter,
  SourceComponentFilter,
  UniqueFilter
} from "./Filters";

import ClearAllFilters from "./ClearAllFilters";
import RemoveFilteredReports from "./RemoveFilteredReports";
import ReportCount from "./ReportCount";

export default {
  name: "ReportFilter",
  components: {
    ClearAllFilters,
    ReportCount,
    UniqueFilter,
    ReportHashFilter,
    BaselineRunFilter,
    BaselineTagFilter,
    NewcheckDiffTypeFilter,
    NewcheckRunFilter,
    NewcheckTagFilter,
    ReviewStatusFilter,
    DetectionStatusFilter,
    SeverityFilter,
    DetectionDateFilter,
    FilePathFilter,
    SourceComponentFilter,
    CheckerNameFilter,
    CheckerMessageFilter,
    RemoveFilteredReports,
    BugPathLengthFilter
  },
  props: {
    namespace: { type: String, required: true },
    showNewcheck: { type: Boolean, default: true },
    showReviewStatus: { type: Boolean, default: true },
    showRemoveFilteredReports: { type: Boolean, default: true },
    reportCount: { type: Number, required: true }
  },

  data() {
    return {
      activeBaselinePanelId: 0,
      activeNewcheckPanelId: 0
    };
  },

  computed: {
    ...mapState({
      cmpData(state) {
        return state[this.namespace].cmpData;
      }
    }),
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

        // Close NEWCHECK expansion panel if no compare data is set.
        if (!this.cmpData?.runIds && !this.cmpData?.runTag) {
          this.activeNewcheckPanelId = -1;
        }
      });
    },

    clearAllFilters() {
      const filters = this.$refs.filters;

      // Unregister watchers.
      this.unregisterWatchers();
      filters.forEach(filter => filter.unregisterWatchers());

      // Clear all filters and update the url.
      filters.forEach(filter => filter.clear(false) );
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

<style lang="scss" scoped>
.v-expansion-panel-header {
  min-height: 40px;
}

.v-expansion-panel-content > ::v-deep .v-expansion-panel-content__wrap {
  padding: 0 4px 0 6px;
}
</style>
