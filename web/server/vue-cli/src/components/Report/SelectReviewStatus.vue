<template>
  <v-dialog
    v-model="dialog"
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
            v-model="value.status"
            :items="items"
            :hide-details="true"
            label="Set review status"
            item-text="label"
            item-value="id"
            height="0"
            dense
            outlined
            @input="onReviewStatusChange"
          >
            <template v-slot:selection="{ item }">
              <v-avatar left>
                <review-status-icon :status="item.id" />
              </v-avatar>
              {{ item.label }}
            </template>

            <template v-slot:item="{ item }">
              <v-avatar left>
                <review-status-icon :status="item.id" />
              </v-avatar>
              {{ item.label }}
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
            v-model="value.comment"
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
          color="error"
          text
          @click="cancelReviewStatusChange"
        >
          Cancel
        </v-btn>

        <v-btn
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
import { ReviewStatus } from "@cc/report-server-types";

import { ReviewStatusIcon } from "@/components/Icons";

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
      console.warning("Non existing review status code: ", reviewCode);
  }
}

export default {
  name: "SelectReviewStatus",
  components: {
    ReviewStatusIcon
  },
  props: {
    value: { type: Object, default: () => {} },
    onConfirm: { type: Function, default: () => {} }
  },
  data() {
    return {
      items: [],
      dialog: false,
      prevValue: null
    };
  },

  created() {
    this.items = Object.values(ReviewStatus).map((id) => {
      return {
        id: id,
        label: reviewStatusFromCodeToString(id)
      };
    });
  },

  methods: {
    onReviewStatusChange() {
      this.dialog = true;
      this.prevValue = { ...this.value };
    },

    confirmReviewStatusChange() {
      if (!this.value.comment || !this.value.comment.length) return;

      this.onConfirm(this.value);
      this.dialog = false;
      this.prevValue = { ...this.value };
    },

    cancelReviewStatusChange() {
      this.dialog = false;
      Object.assign(this.value, this.prevValue);
    }
  }
}
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
