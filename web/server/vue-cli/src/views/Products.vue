<template>
  <v-container fluid>
    <v-data-table
      :headers="headers"
      :items="processedProducts"
      :server-items-length.sync="processedProducts.length"
      :hide-default-footer="true"
      :must-sort="true"
      item-key="endpoint"
    >
      <template v-slot:top>
        <v-toolbar flat class="mb-4">
          <v-row>
            <v-col>
              <v-text-field
                v-model="productNameSearch"
                prepend-inner-icon="mdi-magnify"
                label="Search for products..."
                single-line
                hide-details
                outlined
                solo
                flat
                dense
              />
            </v-col>

            <v-spacer />

            <v-col cols="auto" align="right">
              <v-spacer />

              <span
                v-if="isSuperUser"
              >
                <edit-announcement-btn />

                <edit-global-permission-btn />

                <new-product-btn
                  :is-super-user="isSuperUser"
                  @on-complete="onCompleteNewProduct"
                />
              </span>
            </v-col>
          </v-row>
        </v-toolbar>
      </template>

      <template #item.displayedName="{ item }">
        <v-list-item
          class="pa-0"
          two-line
        >
          <v-list-item-avatar class="my-1">
            <v-avatar
              :color="strToColor(item.endpoint)"
              size="48"
              class="my-1"
            >
              <span class="white--text headline">
                {{ item.endpoint | productIconName }}
              </span>
            </v-avatar>
          </v-list-item-avatar>

          <v-list-item-content>
            <v-list-item-title>
              <span
                v-if="item.databaseStatus !== DBStatus.OK || !item.accessible"
                :style="{ 'text-decoration': 'line-through' }"
              >
                {{ item.displayedName }}
              </span>

              <router-link
                v-else
                :to="{ name: 'runs', params: { endpoint: item.endpoint } }"
              >
                {{ item.displayedName }}
              </router-link>

              <span
                v-if="!item.accessible"
                color="grey--text"
              >
                <v-icon>mdi-alert-outline</v-icon>
                You do not have access to this product!
              </span>

              <span
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
              </span>
            </v-list-item-title>

            <v-list-item-subtitle>
              {{ item.description }}
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
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
          class="mr-2 my-1"
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
        <div class="text-no-wrap">
          <edit-product-btn
            v-if="isSuperUser || item.administrating"
            :product="item"
            :is-super-user="isSuperUser"
            @on-complete="onCompleteEditProduct"
          />

          <delete-product-btn
            v-if="isSuperUser"
            :product="item"
            @on-complete="deleteProduct"
          />
        </div>
      </template>
    </v-data-table>
  </v-container>
</template>

<script>
import _ from "lodash";

import { authService, handleThriftError, prodService } from "@cc-api";
import { DBStatus, Permission } from "@cc/shared-types";

import { StrToColorMixin } from "@/mixins";
import { EditGlobalPermissionBtn } from "@/components/Product/Permission";
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
    EditGlobalPermissionBtn,
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
          text: "Name",
          value: "displayedName",
          sortable: true
        },
        {
          text: "Admins",
          value: "admins",
          sortable: false
        },
        {
          text: "Number of runs",
          value: "runCount",
          align: "center",
          sortable: true
        },
        {
          text: "Latest store to product",
          value: "latestStoreToProduct",
          sortable: true
        },
        {
          text: "Run store in progress",
          value: "runStoreInProgress",
          sortable: false
        },
        {
          text: "Actions",
          value: "action",
          sortable: false
        },
      ],
      products: [],
      isSuperUser: false,
      isAdminOfAnyProduct: false
    };
  },

  computed: {
    processedProducts() {
      const products = [ ...this.products ];
      return products.map(product => {
        product.description = product.description_b64 ?
          window.atob(product.description_b64) : null;
        product.displayedName = product.displayedName_b64 ?
          window.atob(product.displayedName_b64) : null;

        return product;
      }).sort((p1, p2) => {
        // By default sort runs by displayed name and put products to the end
        // of list which are not accessible by the current user.
        if (p1.accessible === p2.accessible) {
          if (p1.displayedName.toLowerCase() < p2.displayedName.toLowerCase()) {
            return -1;
          }

          if (p1.displayedName.toLowerCase() > p2.displayedName.toLowerCase()) {
            return 1;
          }

          return 0;
        } else {
          return p1.accessible ? -1 : 1;
        }
      });
    }
  },

  watch: {
    productNameSearch: _.debounce(function () {
      this.$router.replace({
        query: {
          ...this.$route.query,
          "name": this.productNameSearch
            ? this.productNameSearch : undefined
        }
      }).catch(() => {});

      this.fetchProducts();
    }, 500),
  },

  created() {
    this.productNameSearch = this.$router.currentRoute.query["name"] || null;

    authService.getClient().hasPermission(Permission.SUPERUSER, "",
      handleThriftError(isSuperUser => {
        this.isSuperUser = isSuperUser;

        if (!isSuperUser) {
          prodService.getClient().isAdministratorOfAnyProduct(
            handleThriftError(isAdminOfAnyProduct => {
              this.isAdminOfAnyProduct = isAdminOfAnyProduct;

              // Remove action column from headers.
              if (!isAdminOfAnyProduct) {
                this.headers = this.headers.filter(header => {
                  return header.value !== "action";
                });
              }
            }));
        }
      }));

    if (!this.productNameSearch) {
      this.fetchProducts();
    }
  },

  methods: {
    fetchProducts() {
      const productNameFilter = this.productNameSearch
        ? `*${this.productNameSearch}*` : null;

      prodService.getClient().getProducts(null, productNameFilter,
        handleThriftError(products => {
          this.products = products;
        }));
    },

    onCompleteNewProduct() {
      this.fetchProducts();
    },

    onCompleteEditProduct() {
      this.fetchProducts();
    },

    deleteProduct(product) {
      this.products = this.products.filter(p => p.id !== product.id);
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
};
</script>
