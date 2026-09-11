<template>
  <v-tooltip
    location="bottom"
    color="white"
    content-class="analyzer-statistics-tooltip"
    open-delay="100"
  >
    <template v-slot:activator="{ props: tooltipProps }">
      <component
        :is="tag"
        v-bind="{ ...tooltipProps, ...$attrs }"
        class="analyzer-statistics d-inline-flex align-center"
      >
        <v-chip
          variant="tonal"
          color="primary"
        >
          <v-icon start size="16">
            mdi-cog-outline
          </v-icon>
          {{ analyzerCount }}
        </v-chip>

        <v-divider
          v-if="totalSuccessful || totalFailed"
          class="mx-2 d-inline"
          inset
          vertical
        />

        <v-chip
          v-if="totalSuccessful"
          variant="tonal"
          color="success"
          class="mr-1"
        >
          <analyzer-statistics-icon value="successful" class="mr-1" />
          {{ totalSuccessful }}
        </v-chip>

        <v-chip
          v-if="totalFailed"
          variant="tonal"
          color="error"
        >
          <analyzer-statistics-icon value="failed" class="mr-1" />
          {{ totalFailed }}
        </v-chip>
      </component>
    </template>

    <v-card
      class="analyzer-statistics-tooltip-card"
      variant="elevated"
    >
      <v-list density="compact">
        <v-list-item
          v-for="analyzer in analyzers"
          :key="analyzer.name"
          class="text-no-wrap"
        >
          <template v-slot:title>
            <b>{{ analyzer.name }}</b>
          </template>

          <template v-slot:append>
            <span
              v-if="analyzer.successful !== 0"
              class="ml-3"
              title="Number of successfully analyzed files."
            >
              <analyzer-statistics-icon value="successful" />
              {{ analyzer.successful }}
            </span>
            <span
              v-if="analyzer.failed !== 0"
              class="ml-3"
              title="Number of files which failed to analyze."
            >
              <analyzer-statistics-icon value="failed" />
              {{ analyzer.failed }}
            </span>
          </template>
        </v-list-item>
      </v-list>
    </v-card>
  </v-tooltip>
</template>

<script setup>
import { AnalyzerStatisticsIcon } from "@/components/Icons";
import { computed } from "vue";

const props = defineProps({
  value: { type: Object, required: true },
  tag: { type: String, default: "span" }
});

defineOptions({
  inheritAttrs: false
});

const analyzers = computed(function() {
  return Object.keys(props.value).map(function(name) {
    return {
      name,
      successful: props.value[name].successful.toNumber(),
      failed: props.value[name].failed.toNumber()
    };
  });
});

const analyzerCount = computed(function() {
  return analyzers.value.length;
});

const totalSuccessful = computed(function() {
  return analyzers.value.reduce((sum, a) => sum + a.successful, 0);
});

const totalFailed = computed(function() {
  return analyzers.value.reduce((sum, a) => sum + a.failed, 0);
});
</script>

<style lang="scss">
  .analyzer-statistics {
    cursor: pointer;

    &:hover {
      color: var(--v-primary-base);
    }
  }

  .analyzer-statistics-tooltip-card {
    max-height: 300px;
    overflow-y: auto;
    background-color: white !important;
  }

  .analyzer-statistics-tooltip {
    background-color: white !important;
    padding: 0 !important;
    box-shadow: none !important;
  }
</style>

