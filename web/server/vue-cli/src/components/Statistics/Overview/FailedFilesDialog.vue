<template>
  <v-dialog
    v-model="dialog"
    content-class="documentation-dialog"
    max-width="80%"
    scrollable
  >
    <template v-slot:activator="{ props }">
      <slot :on="props" />
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Failed files

        <v-spacer />

        <v-btn
          class="close-btn"
          icon="mdi-close"
          @click="dialog = false"
        />
      </v-card-title>

      <v-card-text class="pa-0">
        <v-card :loading="loading" flat>
          <v-container>
            <v-table>
              <template v-slot:default>
                <thead>
                  <tr>
                    <th class="text-left">
                      File path
                    </th>
                    <th class="text-left">
                      Failed to analyze in these runs
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="file in files"
                    :key="file"
                  >
                    <td>
                      {{ file }}
                    </td>
                    <td>
                      <v-chip
                        v-for="i in failedFiles[file]"
                        :key="i.runName"
                        color="#878d96"
                        variant="outlined"
                        size="small"
                      >
                        {{ i.runName }}
                      </v-chip>
                    </td>
                  </tr>
                </tbody>
              </template>
            </v-table>
          </v-container>
        </v-card>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";

import { ccService, handleThriftError } from "@cc-api";

const dialog = ref(false);
const loading = ref(false);
const failedFiles = ref({});

const files = computed(function() {
  return Object.keys(failedFiles.value).sort((_a, _b) => _a.localeCompare(_b));
});

watch(dialog, function() {
  loading.value = true;
  ccService.getClient().getFailedFiles(null,
    handleThriftError(_res => {
      failedFiles.value = _res;
      loading.value = false;
    }));
});
</script>
