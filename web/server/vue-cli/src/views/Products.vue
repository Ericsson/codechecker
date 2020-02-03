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

        <new-product-btn
          @on-complete="onCompleteNewProduct"
        />
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
      <span
        v-if="item.databaseStatus !== DBStatus.OK || !item.accessible"
        :style="{ 'text-decoration': 'line-through' }"
      >
        {{ item.endpoint }}
      </span>

      <router-link
        v-else
        :to="{ name: 'runs', params: { endpoint: item.endpoint } }"
      >
        {{ item.endpoint }}
      </router-link>
    </template>

    <template #item.description="{ item }">
      <div
        v-if="!item.accessible"
        color="grey--text"
      >
        <v-icon>mdi-alert-outline</v-icon>
        You do not have access to this product!
      </div>

      <div
        v-else-if="item.databaseStatus !== DBStatus.OK"
        class="error--text"
      >
        <v-icon>mdi-alert-outline</v-icon>
        {{ dbStatusFromCodeToString(item.databaseStatus) }}
        <span
          v-if="item.databaseStatus === DBStatus.SCHEMA_MISMATCH_OK ||
            item.databaseStatus === DBStatus.SCHEMA_MISSING"
        >
          Use <kbd>CodeChecker server</kbd> command for schema
          upgrade/initialization.
        </span>
      </div>

      {{ item.description }}
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

    <template #item.runCount="{ item }">
      <v-chip
        :color="getRunCountColor(item.runCount)"
        dark
      >
        {{ item.runCount }}
      </v-chip>
    </template>

    <template #item.latestStoreToProduct="{ item }">
      <v-chip
        v-if="item.latestStoreToProduct"
        class="ma-2"
        color="primary"
        outlined
      >
        <v-icon left>
          mdi-calendar-range
        </v-icon>
        {{ item.latestStoreToProduct | prettifyDate }}
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
      <edit-product-btn
        :product="item"
        @on-complete="onCompleteEditProduct"
      />

      <delete-product-btn
        :product="item"
        @on-complete="deleteProduct"
      />
    </template>
  </v-data-table>
</template>

<script>
import { prodService } from "@cc-api";
import { DBStatus } from "@cc/shared-types";

import { StrToColorMixin } from "@/mixins";
import {
  DeleteProductBtn,
  EditAnnouncementBtn,
  EditProductBtn,
  NewProductBtn
} from "@/components/Product/";

export default {
  name: "Products",
  filters: {
    productIconName: function (endpoint) {
      if (!endpoint) return "";

      return endpoint.charAt(0).toUpperCase();
    }
  },
  components: {
    DeleteProductBtn,
    EditAnnouncementBtn,
    EditProductBtn,
    NewProductBtn
  },
  mixins: [ StrToColorMixin ],

data() {
    return {
      DBStatus,
      productNameSearch: null,
      headers: [
        {
          text: "",
          value: "icon",
          width: "1%"
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
          value: "runCount",
          align: "center"
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

    onCompleteNewProduct() {
      this.fetchProducts();
    },

    onCompleteEditProduct() {
      this.fetchProducts();
    },

    deleteProduct(product) {
      this.products = this.products.filter((p) => p.id !== product.id);
    },

    dbStatusFromCodeToString(dbStatus) {
      switch (parseInt(dbStatus)) {
        case DBStatus.OK:
          return "Database is up to date.";
        case DBStatus.MISSING:
          return "Database is missing.";
        case DBStatus.FAILED_TO_CONNECT:
          return "Failed to connect to the database.";
        case DBStatus.SCHEMA_MISMATCH_OK:
          return "Schema mismatch: migration is possible.";
        case DBStatus.SCHEMA_MISMATCH_NO:
          return "Schema mismatch: migration not available.";
        case DBStatus.SCHEMA_MISSING:
          return "Schema is missing.";
        case DBStatus.SCHEMA_INIT_ERROR:
          return "Schema initialization error.";
        default:
          console.warn("Non existing database status code: ", dbStatus);
          return "N/A";
      }
    },

    getRunCountColor(runCount) {
      if (runCount > 500) {
        return "red";
      } else if (runCount > 200) {
        return "orange";
      } else {
        return "green";
      }
    }
  }
}
</script>
