<template>
  <v-container fluid>
    <v-data-table
      :headers="headers"
      :items="products"
      :options.sync="pagination"
      :server-items-length.sync="products.length"
      :hide-default-footer="true"
      :must-sort="true"
      :loading="loading"
      :mobile-breakpoint="1000"
      loading-text="Loading products..."
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

              <v-btn
                icon
                title="Reload products"
                color="primary"
                @click="fetchProducts"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </v-toolbar>
      </template>

      <template #item.displayedName="{ item }">
        <product-name-column :product="item" />
      </template>

      <template #item.admins="{ item }">
        <span
          v-for="admin in item.admins"
          :key="admin"
          class="v-chip-max-width-wrapper"
        >
          <v-chip
            color="secondary"
            class="mr-2 my-1"
            outlined
            :title="admin"
          >
            <v-avatar>
              <v-icon>mdi-account-circle</v-icon>
            </v-avatar>
            {{ admin }}
          </v-chip>
        </span>
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
        <span
          v-for="runName in item.runStoreInProgress"
          :key="runName"
          class="v-chip-max-width-wrapper"
        >
          <v-chip
            class="mr-2 my-1"
            color="accent"
          >
            <v-avatar>
              <v-icon>mdi-play-circle</v-icon>
            </v-avatar>
            {{ runName }}
          </v-chip>
        </span>
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

import { EditGlobalPermissionBtn } from "@/components/Product/Permission";
import {
  DeleteProductBtn,
  EditAnnouncementBtn,
  EditProductBtn,
  NewProductBtn,
  ProductNameColumn
} from "@/components/Product/";

export default {
  name: "Products",
  components: {
    DeleteProductBtn,
    EditAnnouncementBtn,
    EditGlobalPermissionBtn,
    EditProductBtn,
    NewProductBtn,
    ProductNameColumn
  },

  data() {
    const sortBy = this.$router.currentRoute.query["sort-by"];
    const sortDesc = this.$router.currentRoute.query["sort-desc"];

    return {
      DBStatus,
      productNameSearch: null,
      loading: false,
      pagination: {
        sortBy: sortBy ? [ sortBy ] : [],
        sortDesc: sortDesc !== undefined ? [ !!sortDesc ] : []
      },
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

  watch: {
    pagination: {
      handler() {
        const sortBy = this.pagination.sortBy.length
          ? this.pagination.sortBy[0] : undefined;
        const sortDesc = this.pagination.sortDesc.length
          ? this.pagination.sortDesc[0] : undefined;

        this.$router.replace({
          query: {
            ...this.$route.query,
            "sort-by": sortBy,
            "sort-desc": sortDesc,
          }
        }).catch(() => {});

        this.products.sort(this.sortProducts);
      },
      deep: true
    },

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
      this.loading = true;

      const productNameFilter = this.productNameSearch
        ? `*${this.productNameSearch}*` : null;

      prodService.getClient().getProducts(null, productNameFilter,
        handleThriftError(products => {
          this.products = products.map(product => {
            const description = product.description_b64 ?
              window.atob(product.description_b64) : null;
            const displayedName = product.displayedName_b64 ?
              window.atob(product.displayedName_b64) : null;

            return {
              description,
              displayedName,
              ...product
            };
          }).sort(this.sortProducts);

          this.loading = false;
        }));
    },

    sortProducts(p1, p2) {
      const sortBy = this.pagination.sortBy.length
        ? this.pagination.sortBy[0] : undefined;
      const sortDesc = this.pagination.sortDesc.length
        ? this.pagination.sortDesc[0] : undefined;

      let p1Value = null;
      let p2Value = null;

      if (sortBy === undefined) {
        // By default sort runs by displayed name and put products to the end
        // of list which are not accessible by the current user.
        if (p1.accessible !== p2.accessible) return p1.accessible ? -1 : 1;

        p1Value = p1.displayedName.toLowerCase();
        p2Value = p2.displayedName.toLowerCase();
      } else if (sortBy === "displayedName") {
        p1Value = p1.displayedName.toLowerCase();
        p2Value = p2.displayedName.toLowerCase();
      } else if (sortBy === "runCount") {
        p1Value = p1.runCount;
        p2Value = p2.runCount;
      } else if (sortBy === "latestStoreToProduct") {
        p1Value = p1.latestStoreToProduct
          ? new Date(p1.latestStoreToProduct)
          : null;
        p2Value = p2.latestStoreToProduct
          ? new Date(p2.latestStoreToProduct)
          : null;
      } else {
        console.warn("Invalid sort field: ", sortBy);
      }

      if (sortDesc) [ p1Value, p2Value ] = [ p2Value, p1Value ];

      if (p1Value < p2Value) return -1;
      if (p1Value > p2Value) return 1;

      return 0;
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

<style lang="scss" scoped>
.v-list-item__subtitle {
  white-space: normal;
}

.v-chip-max-width-wrapper {
  display: inline-block;
  max-width: 150px;

  ::v-deep .v-chip__content {
    line-height: 32px;
    display: inline-block !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    position: relative;
  }
}
</style>