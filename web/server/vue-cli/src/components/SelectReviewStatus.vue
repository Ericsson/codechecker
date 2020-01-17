<template>
  <v-select
    label="Set review status"
    :items="items"
    item-text="label"
    item-value="id"
    dense
    solo
    @input="changeReviewStatus"
  >
    <template v-slot:selection="{ item }">
      <v-list-item-icon class="mr-2">
        <review-status-icon :status="item.id" />
      </v-list-item-icon>

      <v-list-item-content>
        <v-list-item-title v-text="item.label" />
      </v-list-item-content>
    </template>

    <template v-slot:item="{ item }">
      <v-list-item-icon class="mr-2">
        <review-status-icon :status="item.id" />
      </v-list-item-icon>

      <v-list-item-content>
        <v-list-item-title v-text="item.label" />
      </v-list-item-content>
    </template>
  </v-select>
</template>

<script>
import VSelect from "Vuetify/VSelect/VSelect";
import {
  VListItemContent,
  VListItemIcon,
  VListItemTitle
} from "Vuetify/VList";

import { ReviewStatus } from "@cc/report-server-types";

import { ReviewStatusIcon } from "@/components/icons";

function reviewStatusFromCodeToString(reviewCode) {
  switch (parseInt(reviewCode)) {
    case ReviewStatus.UNREVIEWED:
      return 'Unreviewed';
    case ReviewStatus.CONFIRMED:
      return 'Confirmed';
    case ReviewStatus.FALSE_POSITIVE:
      return 'False positive';
    case ReviewStatus.INTENTIONAL:
      return "Intentional";
    default:
      console.warning('Non existing review status code: ', reviewCode);
  }
}

export default {
  name: "SelectReviewStatus",
  components: {
    VSelect, VListItemContent, VListItemIcon, VListItemTitle,
    ReviewStatusIcon
  },
  data() {
    return {
      items: [ ]
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
    changeReviewStatus(value) {
      console.log("Change review status", value);
    }
  }
}
</script>