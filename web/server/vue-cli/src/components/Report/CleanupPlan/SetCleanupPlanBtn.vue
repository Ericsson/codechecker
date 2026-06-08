<template>
  <v-menu
    v-model="menu"
    content-class="set-cleanup-plan-dialog"
    :close-on-content-click="false"
    :nudge-width="100"
    offset-y
  >
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        color="primary"
        class="set-cleanup-plan-btn"
        outlined
        small
        :disabled="!selectedReportHashes.length"
        :loading="loading"
        v-bind="attrs"
        v-on="on"
      >
        <v-icon class="mr-1" small>
          mdi-sign-direction
        </v-icon>
        Set cleanup plan
      </v-btn>

      <tooltip-help-icon>
        You can use <b>cleanup plans</b> to track progress of reports in your
        product.
        <ul>
          <li>
            You can manage cleanup plans from the report filter bar by clicking
            on the pencil icon
            (<v-icon color="white" small>
              mdi-pencil
            </v-icon>)
            beside the <i>Cleanup plan</i> filter.
          </li>
          <li>
            After you created a cleanup plan, with this button you can
            associate it with selected / current report(s).
          </li>
          <li>
            You can list reports associated with a cleanup plan by using the
            <i>Cleanup plan</i> filter.
          </li>
        </ul>
      </tooltip-help-icon>
    </template>

    <v-card>
      <v-list-item-group
        :value="changedSelectedItems"
        multiple
        @change="updateSelectedCleanupPlans"
      >
        <cleanup-plan-tab v-model="tab">
          <template v-slot:open>
            <cleanup-plan-list
              :value="openCleanupPlans"
              :not-all-selected="changedNotAllSelected"
            />
          </template>

          <template v-slot:closed>
            <cleanup-plan-list
              :value="closedCleanupPlans"
              :not-all-selected="changedNotAllSelected"
            />
          </template>
        </cleanup-plan-tab>
      </v-list-item-group>
    </v-card>
  </v-menu>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import CleanupPlanTab from "./CleanupPlanTab";
import CleanupPlanTabMixin from "./CleanupPlanTab.mixin";
import CleanupPlanList from "./CleanupPlanList";

export default {
  name: "SetCleanupPlanBtn",
  components: {
    CleanupPlanList,
    CleanupPlanTab,
    TooltipHelpIcon,
  },
  mixins: [ CleanupPlanTabMixin ],
  props: {
    value: { type: Array, required: true }
  },
  data() {
    return {
      menu: false,
      origSelectedItems: [],
      changedSelectedItems: [],
      origNotAllSelected: {},
      changedNotAllSelected: {}
    };
  },
  computed: {
    selectedReportHashes() {
      return [ ...new Set(this.value.map(v => v.bugHash)) ];
    }
  },
  watch: {
    menu() {
      if (!this.menu) {
        this.save();
        this.reset();
      } else {
        this.fetchCleanupPlans();
      }
    }
  },
  methods: {
    reset() {
      this.openCleanupPlans = null;
      this.closedCleanupPlans = null;
      this.origSelectedItems = [];
      this.changedSelectedItems = [];
      this.origNotAllSelected = {};
      this.changedNotAllSelected = {};
    },

    save() {
      this.getCheckedCleanups().forEach(cleanupPlanId => {
        ccService.getClient().setCleanupPlan(cleanupPlanId,
          this.selectedReportHashes, handleThriftError());
      });

      this.getUncheckedCleanups().forEach(cleanupPlanId => {
        ccService.getClient().unsetCleanupPlan(cleanupPlanId,
          this.selectedReportHashes, handleThriftError());
      });
    },

    getCheckedCleanups() {
      return this.changedSelectedItems.filter(s =>
        !this.origSelectedItems.includes(s));
    },

    getUncheckedCleanups() {
      const removeFromCleanups = [];

      this.origSelectedItems.forEach(s => {
        if (!this.changedSelectedItems.includes(s)) {
          removeFromCleanups.push(s);
        }
      });
      Object.keys(this.origNotAllSelected).forEach(s => {
        if (
          !(s in this.changedNotAllSelected) &&
          !this.changedSelectedItems.includes(s)
        ) {
          removeFromCleanups.push(s);
        }
      });

      return removeFromCleanups;
    },

    // Initialize selected items.
    onFetchFinished(cleanupPlans) {
      cleanupPlans.forEach(cleanupPlan => {
        const id = cleanupPlan.id.toNumber();

        const commonReportHashes = this.selectedReportHashes.filter(
          reportHash => cleanupPlan.reportHashes.includes(reportHash));

        if (
          commonReportHashes.length === this.selectedReportHashes.length
        ) {
          // Every selected report hashes are in the current cleanup plan so
          // mark it as active.
          if (!this.origSelectedItems.includes(id)) {
            this.origSelectedItems.push(id);
            this.changedSelectedItems.push(id);
          }
        } else if (commonReportHashes.length !== 0) {
          // Not all selected report hashes are in the cleanup plan, so mark
          // it differently.
          this.origNotAllSelected[id] = true;
          this.changedNotAllSelected[id] = true;
        }
      });
    },

    updateSelectedCleanupPlans(cleanupPlanIds) {
      cleanupPlanIds.forEach(id => {
        if (!this.changedSelectedItems.includes(id)) {
          delete this.changedNotAllSelected[id];
        }
      });

      this.changedSelectedItems = cleanupPlanIds;
    }
  }
};
</script>
