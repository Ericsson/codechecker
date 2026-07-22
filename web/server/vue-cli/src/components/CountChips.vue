<template>
  <span
    class="count-chips"
  >
    <component
      :is="tag"
      class="text-no-wrap"
    >
      <v-chip
        v-if="props.numGood > 0"
        color="success"
        :ripple="false"
        :title="goodText"
        variant="outlined"
        size="x-small"
        prepend-icon="mdi-check"
        @click="emit('showing-good-click')"
      >
        {{ numGood }}
      </v-chip>

      <v-chip
        v-if="props.numBad > 0 "
        color="error"
        :ripple="false"
        :title="badText"
        variant="outlined"
        size="x-small"
        prepend-icon="mdi-close"
        @click="emit('showing-bad-click')"
      >
        {{ numBad }}
      </v-chip>
      <v-chip
        v-if="props.numUnknown > 0 "
        color="warning"
        :ripple="false"
        :title="unknownText"
        variant="outlined"
        size="x-small"
        prepend-icon="mdi-help"
        @click="emit('showing-unknown-click')"
      >
        {{ numUnknown }}
      </v-chip>

    </component>
  </span>
</template>

<script setup>
const props = defineProps({
  tag: { type: String, default: "span" },
  numGood: { type: Number, default: 0 },
  numBad: { type: Number, default: 0 },
  numUnknown: { type: Number, default: 0 },
  numTotal: { type: Number, default: 0 },
  goodText: { type: String, default: "" },
  badText: { type: String, default: "" },
  unkownText: { type: String, default: "" },
  showZeroChips: { type: Boolean, default: false },
});

const emit = defineEmits([ "showing-good-click",
  "showing-bad-click","showing-unknown-click" ]);

</script>
