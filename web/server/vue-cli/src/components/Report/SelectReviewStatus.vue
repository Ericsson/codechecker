<template>
  <v-dialog
    v-model="dialog"
    content-class="select-review-status-dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{}">
      <v-container fluid class="px-0">
        <v-row>
          <v-col
            cols="auto"
            class="pa-0 mx-4"
          >
            <v-select
              :value="value.status"
              :items="items"
              :hide-details="true"
              :menu-props="{ contentClass: 'select-review-status-menu' }"
              :disabled="isReviewStatusDisabled"
              label="Set review status"
              item-text="label"
              item-value="id"
              class="select-review-status small"
              height="0"
              flat
              dense
              solo
              @input="onReviewStatusChange"
            >
              <template v-slot:selection="{ item }">
                <select-review-status-item :item="item" />
              </template>

              <template v-slot:item="{ item }">
                <select-review-status-item :item="item" />
              </template>
            </v-select>
          </v-col>
        </v-row>
      </v-container>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Change review status

        <v-spacer />

        <v-btn icon dark @click="cancelReviewStatusChange">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <p v-if="isClosing">
            When setting review status to false positive or intentional, the
            report is considered as closed. The date of closing is the current
            time.
          </p>

          <v-alert
            v-if="reportsReviewedInSource.length"
            dense
            outlined
            type="error"
          >
            <p>
              Review status of the following reports are given as source code
              comment. Their review status will not change. However, this option
              sets the review status of all reports without source code comment
              even in the future. This may result that a bug is assigned two
              different review statuses. We don't recommend setting review
              status in this interface for reports which already have one as a
              source code comment!
            </p>

            <div
              v-for="r in reportsReviewedInSource"
              :key="parseInt(r.reportId)"
            >
              <detection-status-icon
                :status="r.detectionStatus"
                :size="16"
              />
              <review-status-icon
                :status="r.reviewData.status"
                :size="16"
              />
              <router-link
                :to="{ name: 'report-detail', query: {
                  ...$router.currentRoute.query,
                  'report-id': r.reportId,
                  'report-hash': undefined
                }}"
                target="_blank"
              >
                {{ r.$runName }}:
                {{ r.checkedFile.replace(/^.*[\\/]/, "") }}:
                L{{ r.line }}
                <strong
                  v-if="parseInt(r.reportId) === parseInt(report.reportId)"
                >
                  (current report)
                </strong>
              </router-link>
            </div>
          </v-alert>
          <v-textarea
            v-model="reviewStatusMessage"
            solo
            flat
            outlined
            name="reviewStatusMessage"
            label="(Optionally) Explain the status change..."
            class="pa-0"
            :hide-details="true"
          />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          class="cancel-btn"
          color="error"
          text
          @click="cancelReviewStatusChange"
        >
          Cancel
        </v-btn>

        <v-btn
          class="save-btn"
          color="primary"
          text
          @click="confirmReviewStatusChange"
        >
          Change review status
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { mapGetters } from "vuex";
import { ccService } from "@cc-api";
import { ReviewStatus } from "@cc/report-server-types";
import { ReviewStatusMixin } from "@/mixins";
import { DetectionStatusIcon, ReviewStatusIcon } from "@/components/Icons";
import SelectReviewStatusItem from "./SelectReviewStatusItem";

export default {
  name: "SelectReviewStatus",
  components: {
    DetectionStatusIcon,
    ReviewStatusIcon,
    SelectReviewStatusItem
  },
  mixins: [ ReviewStatusMixin ],
  props: {
    value: { type: Object, default: () => {} },
    report: { type: Object, default: () => {} },
    onConfirm: { type: Function, default: () => {} }
  },
  data() {
    return {
      items: [],
      dialog: false,
      oldReviewStatus: null,
      reviewStatusMessage: null,
      sameReports: null
    };
  },

  computed: {
    ...mapGetters([
      "currentProductConfig",
      "currentUser"
    ]),

    isReviewStatusDisabled() {
      // Disable by default.
      if (!this.currentProductConfig) return true;

      return this.currentProductConfig.isReviewStatusChangeDisabled;
    },

    reportsReviewedInSource() {
      if (!this.sameReports) return [];
      return this.sameReports.filter(
        report => report.reviewData.isInSource);
    },

    isClosing() {
      return this.value.status === ReviewStatus.FALSE_POSITIVE ||
        this.value.status === ReviewStatus.INTENTIONAL;
    }
  },

  created() {
    this.items = Object.values(ReviewStatus).map(id => {
      return {
        id: id,
        label: this.reviewStatusFromCodeToString(parseInt(id))
      };
    });
  },

  methods: {
    async onReviewStatusChange(value) {
      this.oldReviewStatus = this.value.status;
      this.value.status = value;
      this.reviewStatusMessage = this.value.message;

      this.dialog = true;

      this.sameReports = await ccService.getSameReports(this.report.bugHash);
    },

    confirmReviewStatusChange() {
      const comment = this.reviewStatusMessage || "";
      const author = this.currentUser || "Anonymous";
      this.onConfirm(comment, this.value.status, author);
      this.dialog = false;
    },

    cancelReviewStatusChange() {
      this.value.status = this.oldReviewStatus;
      this.dialog = false;
    },

    selectSameReport(reportId) {
      this.$emit("update:report", reportId.toNumber());
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-select__selections input {
  display: none;
}

::v-deep .v-select.v-text-field--outlined {
  .theme--light.v-label {
    background-color: #fff;
  }
}
</style>
