<template>
  <v-data-table
    :headers="headers"
    :items="processedProducts"
    :hide-default-footer="true"
    item-key="endpoint"
  >
    <template v-slot:top>
      <v-toolbar flat class="mb-4">
        <v-text-field
          v-model="productNameSearch"
          append-icon="mdi-magnify"
          label="Search for products..."
          single-line
          hide-details
        />

        <v-spacer />

        <edit-announcement-btn />

        <v-btn color="primary" class="mr-2">
          Edit global permissions <!-- TODO -->
        </v-btn>

        <v-btn color="primary">
          New product <!-- TODO -->
        </v-btn>
      </v-toolbar>
    </template>

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

    <template v-slot:item.action="{ item }">
      <v-icon
        small
        class="mr-2"
        @click="editProduct(item)"
      >
        mdi-pencil
      </v-icon>
      <v-icon
        small
        @click="deleteProduct(item)"
      >
        mdi-delete
      </v-icon>
    </template>
  </v-data-table>
</template>

<script>
import { prodService } from "@cc-api";

import { StrToColorMixin } from "@/mixins";
import { EditAnnouncementBtn } from "@/components/Product/"

export default {
  name: "Products",
  filters: {
    productIconName: function (endpoint) {
      if (!endpoint) return "";

      return endpoint.charAt(0).toUpperCase();
    }
  },
  components: {
    EditAnnouncementBtn
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
        },
        {
          text: "Actions",
          value: "action",
          sortable: false
        },
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
    },

    editProduct(/*product*/) {
      // TODO: implement this feature.
    },

    deleteProduct(/*product*/) {
      // TODO: implement this feature.
    },
  }
}
</script>
