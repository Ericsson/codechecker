<template>
  <select-option
    title="Run Filter"
    :items="items"
    :fetch-items="fetchItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-play-circle
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
  name: 'BaselineRunFilter',
  components: {
    VIcon,
    SelectOption
  },
  props: {
    reportFilter: { type: Object, required: true }
  },
  data() {
    return {
      selected: [],
      items: [],
      loading: false,
      search: {
        placeHolder : 'Search for run names (e.g.: myrun*)...',
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    fetchItems(search=null) {
      this.loading = true;

      const runIds = null;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter['runName'] = search ? [ `${search}*` ] : null;

      const limit = null;
      const offset = 0;

      ccService.getClient().getRunReportCounts(runIds, reportFilter, limit,
      offset, (err, res) => {
        this.items = res.map((run) => {
          return {
            id: run.runId,
            title: run.name,
            count: run.reportCount
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
