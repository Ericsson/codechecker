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
        variant="outlined"
        size="small"
        @click="emit('showing-good-click')"
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
        vertical
      />

      <v-chip
        v-if="showingBad"
        color="error"
        :ripple="false"
        :title="badText"
        variant="outlined"
        size="small"
        @click="emit('showing-bad-click')"
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
        vertical
      />

      <v-chip
        v-if="showingTotal"
        color="grey-lighten-1"
        :ripple="false"
        :title="totalText"
        variant="elevated"
        size="small"
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

<script setup>
import { computed } from "vue";
const props = defineProps({
  tag: { type: String, default: "span" },
  numGood: { type: Number, default: 0 },
  numBad: { type: Number, default: 0 },
  numTotal: { type: Number, default: 0 },
  goodText: { type: String, default: "" },
  badText: { type: String, default: "" },
  totalText: { type: String, default: "" },
  showDividers: { type: Boolean, default: true },
  showZeroChips: { type: Boolean, default: false },
  showTotal: { type: Boolean, default: false },
  simplifyShowingIfAll: { type: Boolean, default: true }
});

const emit = defineEmits([ "showing-good-click", "showing-bad-click" ]);

const total = computed(() => 
  props.numTotal > 0 ? props.numTotal : (props.numGood + props.numBad)
);

const canSimplify = computed(() => 
  props.simplifyShowingIfAll && 
  (total.value === props.numGood || total.value === props.numBad)
);

const needToShowBothGoodAndBad = computed(() => 
  !canSimplify.value && 
  (props.showZeroChips || (props.numGood > 0 && props.numBad > 0))
);

const showingGood = computed(() => 
  needToShowBothGoodAndBad.value || props.numGood > 0 ||
  (canSimplify.value && total.value === props.numGood)
);

const showingBad = computed(() => 
  needToShowBothGoodAndBad.value || props.numBad > 0 ||
  (props.simplifyShowingIfAll && total.value === props.numBad)
);

const showingTotal = computed(() => 
  props.showTotal && !canSimplify.value &&
  (total.value > 0 || (total.value === 0 && props.showZeroChips))
);
</script>
