<template>
  <v-card
    v-if="Object.keys(formattedHistories).length"
    class="mb-2"
    flat
  >
    <v-timeline
      v-for="(group, date) in formattedHistories"
      :key="date"
      density="compact"
    >
      <v-timeline-item
        class="pb-2"
        icon="mdi-calendar-month"
        fill-dot
        dot-color="accent"
        size="small"
      >
        <strong>{{ date }}</strong>
      </v-timeline-item>

      <v-timeline-item
        v-for="history in group"
        :key="history.id.toNumber()"
        class="run-history pb-2"
        icon="mdi-history"
        fill-dot
        dot-color="primary"
        size="small"
        width="100%"
      >
        <div
          class="d-flex justify-space-between align-center"
        >
          <div>
            <router-link
              :to="{ name: 'reports',
                     query: {
                       run: history.runName,
                       'run-tag': history.id
                     }
              }"
              class="date mr-2"
            >
              <strong>{{ prettifiedTime(history) }}</strong>
            </router-link>
          </div>

          <div>
            <v-list-item
              two-line
            >
              <v-list-item-title>
                <v-chip
                  color="success"
                  variant="outlined"
                  class="mr-2"
                >
                  <v-icon
                    start
                  >
                    mdi-account
                  </v-icon>
                  {{ history.user }}
                </v-chip>

                <version-tag
                  v-if="history.versionTag"
                  :value="history.versionTag"
                />
              </v-list-item-title>

              <v-list-item-subtitle>
                <show-statistics-btn
                  :extra-queries="{
                    run: history.runName,
                    'run-tag': history.id
                  }"
                />

                <v-divider
                  class="mx-2 d-inline"
                  inset
                  vertical="true"
                />

                <analysis-info-dialog
                  :run-id="run?.runId"
                  :run-history-id="history?.id"
                  :icon-only="true"
                  icon-size="default"
                />

                <v-divider
                  class="mx-2 d-inline"
                  inset
                  vertical="true"
                />

                <span :title="history.codeCheckerVersion">
                  v{{ history.$codeCheckerVersion }}
                </span>

                <v-divider
                  class="mx-2 d-inline"
                  inset
                  vertical="true"
                />

                <analyzer-statistics-btn
                  v-if="Object.keys(history.analyzerStatistics).length"
                  :value="history.analyzerStatistics"
                  @click="openAnalyzerStatisticsDialog(null, history)"
                />
              </v-list-item-subtitle>
            </v-list-item>
          </div>

          <v-spacer />

          <div
            class="py-0 d-flex justify-space-between align-center"
          >
            <v-checkbox
              v-model="baselineTags"
              :value="history.id.toNumber()"
              class="ma-0 pa-0"
              hide-details
            />

            <v-checkbox
              v-model="comparedToTags"
              :value="history.id.toNumber()"
              class="ma-0 pa-0"
              hide-details
            />
          </div>
        </div>
      </v-timeline-item>
    </v-timeline>

    <slot />
  </v-card>

  <v-card v-else flat>
    <v-icon>mdi-alert-circle-outline</v-icon>
    <strong>No history events matched your search.</strong>
  </v-card>
</template>

<script setup>
import { useDateUtils } from "@/composables/useDateUtils";
import { format, parse } from "date-fns";
import { computed } from "vue";
import { AnalysisInfoDialog } from "@/components";
import AnalyzerStatisticsBtn from "./AnalyzerStatisticsBtn";
import ShowStatisticsBtn from "./ShowStatisticsBtn";
import VersionTag from "./VersionTag";

const props = defineProps({
  histories: { type: Array, required: true },
  run: { type: Object, required: true },
  openAnalysisInfoDialog: { type: Function, default: () => {} },
  openAnalyzerStatisticsDialog: { type: Function, default: () => {} },
  selectedBaselineTags: { type: Array, required: true },
  selectedComparedToTags: { type: Array, required: true }
});

const emit = defineEmits([
  "update:selected-baseline-tags",
  "update:selected-compared-to-tags"
]);

const { prettifyDate } = useDateUtils();

const baselineTags = computed({
  get() {
    return props.selectedBaselineTags;
  },
  set(newVal) {
    emit("update:selected-baseline-tags", newVal);
  }
});

const comparedToTags = computed({
  get() {
    return props.selectedComparedToTags;
  },
  set(newVal) {
    emit("update:selected-compared-to-tags", newVal);
  }
});

const formattedHistories = computed(function() {
  return props.histories.reduce((acc, curr) => {
    const _date =
      parse(curr.time, "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date());

    const _group = format(_date, "MMMM, yyyy");

    if (!acc[_group])
      acc[_group] = [];

    acc[_group].push(curr);

    return acc;
  }, {});
});

const prettifiedTime = computed(function() {
  return function(history) {
    return prettifyDate(history.time);
  };
});
</script>

<style lang="scss" scoped>
.v-timeline-item.run-history:hover {
  background-color: #eeeeee;
}
</style>
