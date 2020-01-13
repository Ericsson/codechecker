<template>
  <select-option
    title="File path"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-file-document-box-outline
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";
import { ccService } from '@cc-api';

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'FilePathFilter',
  components: {
    VIcon,
    SelectOption
  },
  data() {
    return {
      selected: [],
      items: [],
      loading: false
    };
  },

  methods: {
    fetchItems() {
      this.loading = true;

      const runIds = null;
      const reportFilter = null;
      const cmpData = null;
      const limit = 10;
      const offset = null;

      ccService.getClient().getFileCounts(runIds, reportFilter, cmpData, limit,
      offset, (err, res) => {
        // Order the results alphabetically.
        this.items = Object.keys(res).sort((a, b) => {
            if (a < b) return -1;
            if (a > b) return 1;
            return 0;
        }).map((file) => {
          return {
            id : file,
            title: file,
            count : res[file]
          };
        });

        this.loading = false;
      });
    }
  }
}
</script>
