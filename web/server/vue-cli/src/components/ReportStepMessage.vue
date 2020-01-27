<template>
  <v-chip
    small
    class="report-step-msg"
    :color="color"
    :text-color="textColor"
    :step-id="id"
    :style="{ 'margin-left': marginLeft }"
  >
    <v-avatar left>
      <report-step-enum-icon
        :type="type"
        :index="index"
      />
    </v-avatar>

    <v-btn left text icon small>
      <v-icon>
        mdi-chevron-left
      </v-icon>
    </v-btn>
    

    {{ value }}

    <v-btn right text icon small>
      <v-icon>
        mdi-chevron-right
      </v-icon>
    </v-btn>
  </v-chip>
</template>

<script>
import VChip from "Vuetify/VChip/VChip";
import VAvatar from "Vuetify/VAvatar/VAvatar";
import VIcon from "Vuetify/VIcon/VIcon";
import { VBtn } from "Vuetify/VBtn";

import { ReportStepEnumIcon } from "@/components/icons";

export default {
  name: "EditorBugStep",
  components: {
    VChip, VAvatar, VIcon, VBtn,
    ReportStepEnumIcon
  },
  props: {
    id: { type: [ String, Number ], required: true },
    value: { type: String, required: true },
    marginLeft: { type: String, default: "" },
    type: { type: String, default: null },
    index: { type: Number, default: null }
  },
  computed: {
    color() {
      switch (this.type) {
        case "error":
          return "#f2dede";
        case "fixit":
          return "#fcf8e3";
        default:
          return "#bfdfe9";
      }
    },
    textColor() {
      switch (this.type) {
        case "error":
          return "#a94442";
        case "fixit":
          return "#8a6d3b";
        default:
          return "#00546f";
      }
    }
  }
};
</script>

<style type="scss">
.report-step-msg {
  padding-top: 2px;
  padding-bottom: 2px;
  margin-bottom: 2px;
}
</style>
