<template>
  <v-dialog
    v-model="dialog"
    content-class="select-review-status-dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{}">
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
import { ReviewStatus } from "@cc/report-server-types";
import SelectReviewStatusItem from "./SelectReviewStatusItem";

function reviewStatusFromCodeToString(reviewCode) {
  switch (parseInt(reviewCode)) {
  case ReviewStatus.UNREVIEWED:
    return "Unreviewed";
  case ReviewStatus.CONFIRMED:
    return "Confirmed";
  case ReviewStatus.FALSE_POSITIVE:
    return "False positive";
  case ReviewStatus.INTENTIONAL:
    return "Intentional";
  default:
    console.warn("Non existing review status code: ", reviewCode);
  }
}

export default {
  name: "SelectReviewStatus",
  components: {
    SelectReviewStatusItem
  },
  props: {
    value: { type: Object, default: () => {} },
    onConfirm: { type: Function, default: () => {} }
  },
  data() {
    return {
      items: [],
      dialog: false,
      oldReviewStatus: null,
      reviewStatusMessage: null
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
    }
  },

  created() {
    this.items = Object.values(ReviewStatus).map(id => {
      return {
        id: id,
        label: reviewStatusFromCodeToString(id)
      };
    });
  },

  methods: {
    onReviewStatusChange(value) {
      this.oldReviewStatus = this.value.status;
      this.value.status = value;
      this.reviewStatusMessage = this.value.message;

      this.dialog = true;
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
