<template>
  <span
    class="count-chips"
  >
    <component
      :is="tag"
      class="text-no-wrap"
    >
      <v-chip
        v-if="showingGood"
        color="success"
        :ripple="false"
        :title="goodText"
        outlined
        dark
        small
      >
        <v-icon
          start
          class="mr-1"
        >
          mdi-check
        </v-icon>
        {{ numGood }}
      </v-chip>

      <v-divider
        v-if="showDividers &&
          ((showingGood && showingBad) || (showingGood && showingTotal))"
        class="mx-2 d-inline"
        inset
        vertical
      />

      <v-chip
        v-if="showingBad"
        color="error"
        :ripple="false"
        :title="badText"
        outlined
        dark
        small
      >
        <v-icon
          start
          class="mr-1"
        >
          mdi-close
        </v-icon>
        {{ numBad }}
      </v-chip>

      <v-divider
        v-if="showDividers && showingBad && showingTotal"
        class="mx-2 d-inline"
        inset
        vertical
      />

      <v-chip
        v-if="showingTotal"
        color="grey lighten-1"
        :ripple="false"
        :title="totalText"
        elevated
        small
      >
        <v-icon
          start
          class="mr-1"
        >
          mdi-sigma
        </v-icon>
        {{ numTotal }}
      </v-chip>
    </component>
  </span>
</template>

<script>
import { AnalyzerStatisticsIcon } from "@/components/Icons";

export default {
  name: "CountChips",
  components: {
    AnalyzerStatisticsIcon
  },
  props: {
    tag: { type: String, default: "span" },
    numGood: { type: Number, required: true },
    numBad: { type: Number, default: 0 },
    numTotal: { type: Number, default: 0 },
    goodText: { type: String, default: "" },
    badText: { type: String, default: "" },
    totalText: { type: String, default: "" },
    showDividers: { type: Boolean, default: true },
    showZeroChips: { type: Boolean, default: false },
    showTotal: { type: Boolean, default: false },
    simplifyShowingIfAll: { type: Boolean, default: true }
  },
  computed: {
    total() {
      return (this.numTotal > 0
        ? this.numTotal
        : (this.numGood + this.numBad));
    },
    canSimplify() {
      return this.simplifyShowingIfAll &&
        (this.total === this.numGood || this.total === this.numBad);
    },
    needToShowBothGoodAndBad() {
      return !this.canSimplify &&
        (this.showZeroChips || (this.numGood > 0 && this.numBad > 0));
    },
    showingGood() {
      return this.needToShowBothGoodAndBad || this.numGood > 0 ||
        (this.canSimplify && this.total === this.numGood);
    },
    showingBad() {
      return this.needToShowBothGoodAndBad || this.numBad > 0 ||
        (this.simplifyShowingIfAll && this.total === this.numBad);
    },
    showingTotal() {
      return this.showTotal && !this.canSimplify &&
        (this.total > 0 || (this.total === 0 && this.showZeroChips));
    }
  }
};
</script>
