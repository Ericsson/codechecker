<template>
  <select-option
    title="Checker name"
    :items="items"
    :fetch-items="fetchItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-account-card-details
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
  name: 'CheckerNameFilter',
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
        placeHolder : 'Search for checker names (e.g.: core*)...',
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    fetchItems(search=null) {
      this.loading = true;

      const runIds = null;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter['checkerName'] = search ? [ `${search}*` ] : null;

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
    },

    filterItems(value) {
      this.fetchItems(value);
    }
  }
}
</script>
