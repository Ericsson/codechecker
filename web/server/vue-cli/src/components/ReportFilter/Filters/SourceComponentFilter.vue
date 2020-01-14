<template>
  <select-option
    title="Source component"
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
  name: 'SourceComponentFilter',
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
      const filter = null;

      ccService.getClient().getSourceComponents(filter, (err, res) => {
        this.items = res.map((component) => {
          return {
            id : component.name,
            title: component.name
          };
        });

        this.loading = false;
      });
    }
  }
}
</script>
