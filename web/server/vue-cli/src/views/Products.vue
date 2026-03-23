<template>
  <v-container fluid>
    <v-data-table
      :headers="headers"
      :items="products"
      :loading="loading"
      :footer-props="footerProps"
      loading-text="Loading products..."
      item-key="endpoint"
      :items-per-page="25"
    >
      <template v-slot:top>
        <v-toolbar
          flat
          class="mb-4"
          color="transparent"
        >
          <v-row>
            <v-col align-self="center">
              <v-text-field
                v-model="productNameSearch"
                class="ml-4"
                label="Search for products..."
                hide-details
                variant="outlined"
                clearable
                density="compact"
              />
            </v-col>

            <v-spacer />

            <v-col cols="auto" align="right">
              <span
                v-if="isSuperUser"
              >
                <v-spacer />

                <edit-announcement-btn />

                <edit-global-permission-btn />

                <new-product-btn
                  :is-super-user="isSuperUser"
                  @on-complete="onCompleteNewProduct"
                />
              </span>

              <v-btn
                icon="mdi-refresh"
                title="Reload products"
                color="primary"
                class="mr-2"
                @click="fetchProducts"
              />
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
            variant="outlined"
            :title="admin"
          >
            <template v-slot:prepend>
              <v-icon
                class="mr-2"
              >
                mdi-account-circle
              </v-icon>
            </template>
            {{ admin }}
          </v-chip>
        </span>
      </template>

      <template #item.runCount="{ item }">
        <v-chip
          :color="getRunCountColor(item.runCount)"
        >
          {{ item.runCount }}
        </v-chip>
      </template>

      <template #item.latestStoreToProduct="{ item }">
        <v-chip
          v-if="item.latestStoreToProduct"
          class="ma-2"
          color="primary"
          variant="outlined"
        >
          <template v-slot:prepend>
            <v-icon
              class="mr-2"
            >
              mdi-calendar-range
            </v-icon>
          </template>
          {{ prettifyDate(item.latestStoreToProduct) }}
        </v-chip>
      </template>

      <template v-slot:item.actions="{ item }">
        <div class="text-no-wrap">
          <edit-product-btn
            v-if="item.administrating"
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

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useDateUtils } from "@/composables/useDateUtils";

import _ from "lodash";

const route = useRoute();
const router = useRouter();
const { prettifyDate } = useDateUtils();

import { authService, handleThriftError, prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";

import { EditGlobalPermissionBtn } from "@/components/Product/Permission";
import {
  DeleteProductBtn,
  EditAnnouncementBtn,
  EditProductBtn,
  NewProductBtn,
  ProductNameColumn
} from "@/components/Product/";

const itemsPerPageOptions = ref([ 25 ]);
const sortBy = ref(null);
const sortDesc = ref(null);
const page = ref(null);
const productNameSearch = ref(null);
const loading = ref(null);
const products = ref([]);
const isSuperUser = ref(false);
const isAdminOfAnyProduct = ref(false);

const pagination = computed(() => ({
  sortBy: sortBy.value ? [ sortBy.value ] : [ ],
  sortDesc: sortDesc.value !== undefined ? [ !!sortDesc.value ] : [ ]
}));

const footerProps = computed(() => ({
  itemsPerPageOptions: itemsPerPageOptions.value
}));

watch(pagination, () => {
  const sortByValue = pagination.value.sortBy.length
    ? pagination.value.sortBy[0] : undefined;
  const sortDescValue = pagination.value.sortDesc.length
    ? pagination.value.sortDesc[0] : undefined;

  router.replace({
    query: {
      "sort-by": sortByValue,
      "sort-desc": sortDescValue,
    }
  }).catch(() => {});

  products.value.sort(sortProducts);
}, { deep: true });

watch(page, () => {
  const page = page === 1 ? undefined : page;
  router.replace({
    query: {
      "page": page
    }
  }).catch(() => {});
});

const debouncedSearchHandler = _.debounce(() => {
  router.replace({
    query: {
      "name": productNameSearch.value || undefined
    }
  }).catch(() => {});

  fetchProducts();
}, 500);

watch(productNameSearch, debouncedSearchHandler);

const headers = ref([
  {
    title: "Name",
    value: "displayedName",
    sortable: true
  },
  {
    title: "Admins",
    value: "admins",
    sortable: false
  },
  {
    title: "Number of runs",
    value: "runCount",
    align: "center",
    sortable: true
  },
  {
    title: "Latest store to product",
    value: "latestStoreToProduct",
    sortable: true
  },
  {
    title: "Actions",
    value: "actions",
    sortable: false
  }, 
]);

onMounted(() => {
  sortBy.value = route.query["sort-by"];
  sortDesc.value = route.query["sort-desc"];
  page.value = parseInt(route.query["page"]) || 1;

  initializeComponent();
});

function fetchProducts() {
  loading.value = true;

  const productNameFilter = productNameSearch.value
    ? `*${productNameSearch.value}*` : null;

  prodService.getClient().getProducts(null, productNameFilter,
    handleThriftError(_products => {
      products.value = _products.map(product => {
        const description = product.description_b64 ?
          window.atob(product.description_b64) : null;
        const displayedName = product.displayedName_b64 ?
          window.atob(product.displayedName_b64) : null;

        return {
          description,
          displayedName,
          ...product
        };
      }).sort(sortProducts);

      pagination.value.page = page.value;

      loading.value = false;
    }));
}

function sortProducts(p1, p2) {
  const sortBy = pagination.value.sortBy.length
    ? pagination.value.sortBy[0] : undefined;
  const sortDesc = pagination.value.sortDesc.length
    ? pagination.value.sortDesc[0] : undefined;

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
}

function onCompleteNewProduct() {
  fetchProducts();
}

function onCompleteEditProduct() {
  fetchProducts();
}

function deleteProduct(product) {
  products.value = products.value.filter(p => p.id !== product.id);
}

function getRunCountColor(runCount) {
  if (runCount > 500) {
    return "red";
  } else if (runCount > 200) {
    return "orange";
  } else {
    return "green";
  }
}

function initializeComponent() {
  productNameSearch.value = route.query["name"] || null;

  authService.getClient().hasPermission(Permission.SUPERUSER, "",
    handleThriftError(superUser => {
      isSuperUser.value = superUser;

      if (!superUser) {
        prodService.getClient().isAdministratorOfAnyProduct(
          handleThriftError(isAdmin => {
            isAdminOfAnyProduct.value = isAdmin;

            if (!isAdmin) {
              headers.value.splice(
                headers.value.findIndex(h => h.value === "actions"), 1
              );
            }
          }));
      }
    }));

  if (!productNameSearch.value) {
    fetchProducts();
  }
}
</script>

<style lang="scss" scoped>
.v-list-item__subtitle {
  white-space: normal;
}

.v-chip-max-width-wrapper {
  display: inline-block;
  max-width: 150px;

  :deep(.v-chip__content) {
    line-height: 32px;
    display: inline-block !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    position: relative;
  }
}
</style>