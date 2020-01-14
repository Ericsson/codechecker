<template>
  <select-option
    title="Checker message"
    :items="items"
    :fetch-items="fetchItems"
    :search="search"
    :loading="loading"
  >
    <template v-slot:icon>
      <v-icon color="grey">
        mdi-message-text-outline
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
  name: 'CheckerMessageFilter',
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
        placeHolder : 'Search for checker messages (e.g.: *deref*)...',
        filterItems: this.filterItems
      }
    };
  },

  methods: {
    fetchItems(search=null) {
      this.loading = true;

      const runIds = null;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter['checkerMsg'] = search ? [ `${search}*` ] : null;

      const cmpData = null;
      const limit = 10;
      const offset = null;

      ccService.getClient().getCheckerMsgCounts(runIds, reportFilter, cmpData,
      limit, offset, (err, res) => {
        this.items = Object.keys(res).map((msg) => {
          return {
            id : msg,
            title: msg,
            count : res[msg]
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
