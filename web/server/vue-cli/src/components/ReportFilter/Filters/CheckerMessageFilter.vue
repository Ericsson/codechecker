<template>
  <select-option
    title="Checker message"
    :items="items"
    :fetch-items="fetchItems"
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

import SelectOption from './SelectOption/SelectOption';

export default {
  name: 'CheckerMessageFilter',
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
    }
  }
}
</script>
