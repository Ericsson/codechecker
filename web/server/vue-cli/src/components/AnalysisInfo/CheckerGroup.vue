<template>
  <div
    class="analyzer-checker-group-panel"
    :data-group-name="group"
  >
    <div
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
            variant="outlined"
            size="small"
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
          <CountChips
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
    </div>
    <div>
      <CheckerRows
        :checkers="checkers"
      />
    </div>
  </div>
</template>

<script setup>
import CountChips from "@/components/CountChips";
import { CountKeys } from "@/composables/useAnalysisInfo";
import { computed } from "vue";
import CheckerRows from "./CheckerRows";

const props = defineProps({
  group: { type: String, required: true },
  checkers: { type: Array, required: true },
  counts: { type: Array, required: true }
});

const numEnabled = computed(
  () => props.counts[CountKeys.Enabled]
);

const numDisabled = computed(
  () => props.counts[CountKeys.Disabled]
);

const needDetailedCounts = computed(() => 
  numEnabled.value > 0 && numDisabled.value > 0
);

const groupWideStatus = computed(() => {
  if (numEnabled.value > 0 && numDisabled.value === 0)
    return "success";
  if (numEnabled.value === 0 && numDisabled.value > 0)
    return "error";
  return "grey darken-1";
});

const groupEnabled = computed(() => groupWideStatus.value === "success");
</script>

<style lang="scss" scoped>
.analysis-info .checker-group-name {
  font-family: monospace;
  font-size: 112.5%;
  font-style: italic;
  font-weight: medium;
}
</style>
