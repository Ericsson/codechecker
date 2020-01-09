<template>
  <v-card>
    <v-card-title>
      <v-text-field
        v-model="productNameSearch"
        append-icon="mdi-magnify"
        label="Search for products..."
        single-line
        hide-details
      />
    </v-card-title>

    <v-data-table
      :headers="headers"
      :items="processedProducts"
      :hide-default-footer="true"
      item-key="endpoint"
    >
      <template #item.icon="{ item }">
        <v-avatar
          :color="strToColor(item.endpoint)"
          size="48"
          class="my-1"
        >
          <span class="white--text headline">
            {{ item.endpoint | productIconName }}
          </span>
        </v-avatar>
      </template>

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
  </v-card>
</template>

<script>
import VDataTable from "Vuetify/VDataTable/VDataTable";
import VChip from "Vuetify/VChip/VChip";
import VAvatar from "Vuetify/VAvatar/VAvatar";
import VIcon from "Vuetify/VIcon/VIcon";
import { VCard, VCardTitle } from "Vuetify/VCard";
import VTextField from "Vuetify/VTextField/VTextField";

import { prodService } from '@cc-api';

import { StrToColorMixin } from '@/mixins';

export default {
  name: 'Products',
  components: {
    VDataTable, VChip, VAvatar, VIcon, VCard, VCardTitle, VTextField
  },
  filters: {
    productIconName: function (endpoint) {
      if (!endpoint) return '';

      return endpoint.charAt(0).toUpperCase();
    }
  },
  mixins: [ StrToColorMixin ],

  data() {
    return {
      productNameSearch: null,
      headers: [
        {
          text: "",
          value: "icon"
        },
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

  watch: {
    productNameSearch: function() {
      this.fetchProducts();
    }
  },

  created() {
    this.fetchProducts();
  },

  methods: {
    fetchProducts() {
      const productNameFilter = this.productNameSearch
        ? `*${this.productNameSearch}*` : null;

      prodService.getClient().getProducts(null, productNameFilter,
      (err, products) => {
        this.products = products;
      });
    }
  }
}
</script>
