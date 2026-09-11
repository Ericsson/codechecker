<!-- eslint-disable vue/no-v-html -->
<template>
  <v-container fluid>
    <v-expansion-panels v-model="openPanels" multiple>
      <v-expansion-panel
        v-for="(release, index) in releases"
        :key="release.version"
      >
        <v-expansion-panel-title
          :class="index === 0
            ? 'bg-primary text-white'
            : 'bg-grey-lighten-3'"
        >
          <v-icon
            :color="index === 0 ? 'white' : 'grey-darken-1'"
            class="mr-2"
          >
            mdi-star
          </v-icon>
          <span class="font-weight-medium">
            Highlights of CodeChecker {{ release.version }} release
          </span>

          <span class="ml-2 text-caption">
            · {{ release.features.length }}
            {{ release.features.length === 1 ? "feature" : "features" }}
          </span>

          <v-chip
            v-if="hasBreaking(release)"
            class="ml-3"
            color="error"
            size="small"
            variant="flat"
            prepend-icon="mdi-alert-outline"
          >
            Breaking changes
          </v-chip>

          <v-spacer />

          <v-btn
            :href="release.url"
            target="_blank"
            :color="index === 0 ? 'white' : 'grey-darken-1'"
            icon="mdi-github"
            variant="text"
            density="comfortable"
            title="View release on GitHub"
            @click.stop
          />
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <v-card
            class="mb-4"
            color="grey-lighten-4"
            variant="flat"
            rounded="lg"
          >
            <v-card-title class="text-subtitle-1 font-weight-bold">
              In this release
            </v-card-title>
            <v-card-text>
              <ul class="release-summary">
                <li
                  v-for="feature in release.features"
                  :key="feature.title"
                >
                  {{ feature.title }}
                  <span
                    v-if="feature.breaking"
                    class="text-error font-weight-medium"
                  >
                    (backward incompatible)
                  </span>
                </li>
              </ul>
            </v-card-text>
          </v-card>

          <v-card
            v-for="feature in release.features"
            :key="feature.title"
            class="mb-4"
            color="grey-lighten-4"
            variant="flat"
            rounded="lg"
          >
            <v-card-title class="text-wrap">
              <v-alert
                v-if="feature.breaking"
                density="compact"
                variant="tonal"
                type="error"
                class="mb-2"
              >
                Backward incompatible changes!
              </v-alert>
              {{ feature.title }}
            </v-card-title>

            <v-card-text>
              <template
                v-for="(block, bIndex) in feature.blocks"
                :key="bIndex"
              >
                <div
                  v-if="block.type === 'text'"
                  v-html="block.value"
                />

                <pre
                  v-else-if="block.type === 'code'"
                  class="feature-code"
                >{{ block.value }}</pre>

                <div
                  v-else-if="block.type === 'image'"
                  class="text-center my-2"
                >
                  <img
                    :src="resolveImage(release.version, block.value)"
                    :alt="feature.title"
                    class="feature-image"
                  >
                </div>
              </template>
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script setup>
import { ref } from "vue";

import releases from "./newFeatures.data.js";

// Only the newest release (first in the array) is expanded by default.
const openPanels = ref([ 0 ]);

function hasBreaking(release) {
  return release.features.some(f => f.breaking);
}

function resolveImage(version, file) {
  return require(
    `@/assets/userguide/images/new_features/${version}/${file}`
  );
}
</script>

<style scoped>
.feature-code {
  background-color: rgba(0, 0, 0, 0.04);
  border: thin solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  padding: 8px 12px;
  overflow-x: auto;
  white-space: pre;
  font-size: 0.85em;
}

.feature-image {
  display: inline-block;
  max-width: 100%;
  height: auto;
}

.release-summary {
  margin: 0;
  padding-left: 1.25em;
}

.release-summary li {
  margin-bottom: 4px;
}
</style>
