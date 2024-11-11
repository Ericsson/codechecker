<template>
  <v-dialog
    v-model="dialog"
    content-class="documentation-dialog"
    max-width="80%"
    scrollable
  >
    <template v-slot:activator="{ on }">
      <slot :on="on" />
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Failed files

        <v-spacer />

        <v-btn class="close-btn" icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-card :loading="loading" flat>
          <v-container>
            <v-simple-table>
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
                        outlined
                        small
                      >
                        {{ i.runName }}
                      </v-chip>
                    </td>
                  </tr>
                </tbody>
              </template>
            </v-simple-table>
          </v-container>
        </v-card>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "FailedFilesDialog",
  data() {
    return {
      dialog: false,
      loading: false,
      failedFiles: {}
    };
  },
  computed: {
    files() {
      return Object.keys(this.failedFiles).sort((a, b) => a.localeCompare(b));
    }
  },
  watch: {
    dialog() {
      this.loading = true;
      ccService.getClient().getFailedFiles(null,
        handleThriftError(res => {
          this.failedFiles = res;
          this.loading = false;
        }));
    }
  }
};
</script>
