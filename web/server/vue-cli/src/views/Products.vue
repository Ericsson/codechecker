<template>
  <div>
    <v-data-table
      :headers="headers"
      :items="processedProducts"
      :hide-default-footer="true"
      item-key="endpoint"
    >
      <template #item.endpoint="{ item }">
        <router-link
          :to="{ name: 'runs', params: { endpoint: item.endpoint } }"
        >
          {{ item.endpoint }}
        </router-link>
      </template>

      <template #item.admins="{ item }">
        <v-chip
          v-for="admin in item.admins"
          :key="admin"
          color="secondary"
          class="mr-2"
        >
          <v-avatar left>
            <v-icon>mdi-account-circle</v-icon>
          </v-avatar>
          {{ admin }}
        </v-chip>
      </template>

      <template #item.runStoreInProgress="{ item }">
        <v-chip
          v-for="runName in item.runStoreInProgress"
          :key="runName"
          color="accent"
          class="mr-2"
        >
          <v-avatar left>
            <v-icon>mdi-play-circle</v-icon>
          </v-avatar>
          {{ runName }}
        </v-chip>
      </template>
    </v-data-table>
  </div>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";
import VAvatar from "Vuetify/VAvatar/VAvatar";
import VIcon from "Vuetify/VIcon/VIcon";

import { prodService } from '@cc-api';

export default {
  name: 'Products',
  components: {
    VDataTable, VChip, VAvatar, VIcon
  },

  data() {
    return {
      headers: [
        {
          text: "Name",
          value: "endpoint"
        },
        {
          text: "Description",
          value: "description"
        },
        {
          text: "Admins",
          value: "admins"
        },
        {
          text: "Number of runs",
          value: "runCount"
        },
        {
          text: "Latest store to product",
          value: "latestStoreToProduct"
        },
        {
          text: "Run store in progress",
          value: "runStoreInProgress"
        }
      ],
      products: []
    };
  },

  computed: {
    processedProducts() {
      let products = [ ...this.products ];
      return products.map((product) => {
        product.description = product.description_b64 ?
          window.atob(product.description_b64) : null;

        return product;
      });
    }
  },

  created() {
    this.fetchProducts();
  },

  methods: {
    fetchProducts() {
      prodService.getClient().getProducts(null, null, (err, products) => {
        this.products = products;
      });
    }
  }
}
</script>
