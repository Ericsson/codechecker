<template>
  <v-expansion-panel
    class="analyzer-checker-group-panel"
    :data-group-name="group"
  >
    <v-expansion-panel-header
      class="pa-0 px-1"
    >
      <v-row
        no-gutters
        align="center"
      >
        <v-col cols="auto">
          <v-chip
            class="mr-1 pa-1"
            :color="groupWideStatus"
            :ripple="false"
            :title="'Group \'' + group + '\' was' +
              (needDetailedCounts ? ' partially' :
                (groupEnabled ? '' : ' not')
              ) +
              ' enabled in this analysis'"
            outlined
            dark
            small
          >
            <v-icon
              v-if="!needDetailedCounts && groupEnabled"
              start
            >
              mdi-check
            </v-icon>
            <v-icon
              v-else-if="!needDetailedCounts && !groupEnabled"
              start
            >
              mdi-close
            </v-icon>
            <v-icon
              v-else-if="needDetailedCounts"
              start
            >
              mdi-tune
            </v-icon>
          </v-chip>
        </v-col>
        <v-col
          cols="auto"
          class="pl-2 checker-group-name primary--text"
        >
          {{ group }}
        </v-col>
        <v-col cols="auto">
          <count-chips
            v-if="needDetailedCounts"
            :num-good="counts[CountKeys.Enabled]"
            :num-bad="counts[CountKeys.Disabled]"
            :num-total="counts[CountKeys.Total]"
            :good-text="'Number of checkers enabled (executed)'"
            :bad-text="'Number of checkers disabled (not executed)'"
            :total-text="'Number of checkers available'"
            :simplify-showing-if-all="true"
            :show-total="true"
            :show-dividers="false"
            :show-zero-chips="false"
            class="pl-4"
          />
        </v-col>
      </v-row>
    </v-expansion-panel-header>
    <v-expansion-panel-content>
      <checker-rows
        :checkers="checkers"
      />
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>

<script>
import CountChips from "@/components/CountChips";
import CheckerRows from "./CheckerRows";
import { CountKeys } from "@/mixins/api/analysis-info-handling.mixin";

export default {
  name: "CheckerGroup",
  components: {
    CheckerRows,
    CountChips,
  },
  props: {
    group: { type: String, required: true },
    checkers: { type: Array, required: true },
    counts: { type: Array, required: true }
  },
  computed: {
    numEnabled() {
      return this.counts[this.CountKeys.Enabled];
    },
    numDisabled() {
      return this.counts[this.CountKeys.Disabled];
    },
    needDetailedCounts() {
      return this.numEnabled > 0 && this.numDisabled > 0;
    },
    groupWideStatus() {
      if (this.numEnabled > 0 && this.numDisabled === 0)
        return "success";
      if (this.numEnabled === 0 && this.numDisabled > 0)
        return "error";
      return "grey darken-1";
    },
    groupEnabled() {
      return this.groupWideStatus === "success";
    },
    CountKeys() {
      return CountKeys;
    }
  }
};
</script>

<style lang="scss" scoped>
.analysis-info .checker-group-name {
  font-family: monospace;
  font-size: 112.5%;
  font-style: italic;
  font-weight: medium;
}
</style>
