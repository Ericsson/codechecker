<template>
  <select-option
    title="Tag Filter"
    :items="items"
    :fetch-items="fetchItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-tag
      </v-icon>
    </template>
  </select-option>
</template>

<script>
import VIcon from "Vuetify/VIcon/VIcon";
import { ccService } from '@cc-api';
import { ReportFilter } from '@cc/report-server-types';

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'BaselineTagFilter',
  components: {
    VIcon,
    SelectOption
  },
  data() {
    return {
      selected: [],
      items: [],
      loading: false,
      search: {
        placeHolder : 'Search for run tags...',
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    fetchItems(search=null) {
      this.loading = true;

      const runIds = null;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter['runTag'] = search ? [ `${search}*` ] : null;

      const cmpData = null;

      ccService.getClient().getRunHistoryTagCounts(runIds, reportFilter,
      cmpData, (err, res) => {
        this.items = res.map((tag) => {
          return {
            id: tag.id,
            title: tag.runName + ':' + tag.name,
            count: tag.count
          };
        });

        this.loading = false;
      });
    },

    filterItems(value) {
      this.fetchItems(value);
    }
  }
}
</script>
