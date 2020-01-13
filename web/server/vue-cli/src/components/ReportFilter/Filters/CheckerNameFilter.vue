<template>
  <select-option
    title="Checker name"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-card-bulleted-outline
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";
import { ccService } from '@cc-api';

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'CheckerNameFilter',
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
      const limit = null;
      const offset = 0;

      ccService.getClient().getCheckerCounts(runIds, reportFilter, cmpData,
      limit, offset, (err, res) => {
        this.items = res.map((checker) => {
          return {
            id: checker.name,
            title: checker.name,
            count: checker.count
          };
        });

        this.loading = false;
      });
    }
  }
}
</script>
