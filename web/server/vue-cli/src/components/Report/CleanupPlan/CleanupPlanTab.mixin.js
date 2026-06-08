import { ccService, handleThriftError } from "@cc-api";
import { CleanupPlanFilter } from "@cc/report-server-types";

export default {
  name: "CleanupPlanTabMixin",
  data() {
    return {
      tab: null,
      loading: false,
      openCleanupPlans: null,
      closedCleanupPlans: null,
    };
  },

  watch: {
    tab() {
      this.fetchCleanupPlans(false);
    }
  },

  methods: {
    onFetchFinished(/* cleanupPlans */) {

    },

    fetchCleanupPlans(force=true) {
      if (!this.tab && (!this.openCleanupPlans || force)) {
        this.fetchOpenCleanupPlans();
      } else if (!this.closedCleanupPlans || force) {
        this.fetchClosedCleanupPlans();
      }
    },

    getCleanupPlans(filter) {
      this.loading = true;
      return new Promise(resolve => {
        ccService.getClient().getCleanupPlans(filter,
          handleThriftError(cleanupPlans => {
            this.loading = false;
            resolve(cleanupPlans);
          }));
      });
    },

    async fetchOpenCleanupPlans() {
      const filter = new CleanupPlanFilter({ isOpen: true });
      this.openCleanupPlans = await this.getCleanupPlans(filter);
      this.onFetchFinished(this.openCleanupPlans);
    },

    async fetchClosedCleanupPlans() {
      const filter = new CleanupPlanFilter({ isOpen: false });
      this.closedCleanupPlans = await this.getCleanupPlans(filter);
      this.onFetchFinished(this.closedCleanupPlans);
    },
  }
};
