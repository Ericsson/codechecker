<template>
  <v-container fluid>
    <v-data-table-server
      v-model:page="page"
      v-model:items-per-page="itemsperpage"
      v-model:sort-by="sortBy"
      :headers="headers"
      :items="products"
      :loading="loading"
      :items-per-page-options="itemsPerPageOptions"
      :items-length="itemsLength"
      loading-text="Loading products..."
      item-key="endpoint"
      @update:options="fetchProducts"
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
              <span>
                <edit-announcement-btn
                  v-if="isSuperUser"
                />

                <edit-global-permission-btn
                  v-if="isSuperUser"
                />

                <new-product-btn
                  v-if="isSuperUser"
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
            color="primary"
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
          class="text-black"
          :color="gradientColor.getGradientColor(item.runCount, 500)"
          size="small"
          variant="flat"
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
    </v-data-table-server>
  </v-container>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useDateUtils } from "@/composables/useDateUtils";
import { useGradientColor } from "@/composables/useGradientColor";

import _ from "lodash";

const props = defineProps({
  itemsPerPage: { type: Number, default: 25 },
});

const route = useRoute();
const router = useRouter();
const gradientColor = useGradientColor();
const { prettifyDate } = useDateUtils();


import { authService, handleThriftError, prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";
import { ProductSortMode } from "@cc/prod-types";

import { EditGlobalPermissionBtn } from "@/components/Product/Permission";
import {
  DeleteProductBtn,
  EditAnnouncementBtn,
  EditProductBtn,
  NewProductBtn,
  ProductNameColumn
} from "@/components/Product/";

const itemsPerPageOptions = [
  { value: 25, title: "25" },
  { value: 50, title: "50" },
  { value: 100, title: "100" }
];

const sortBy = ref([]);
const page = ref(null);
const itemsperpage = ref(25);
const productNameSearch = ref(null);
const loading = ref(null);
const products = ref([]);
const isSuperUser = ref(false);
const isAdminOfAnyProduct = ref(false);
const itemsLength = ref(0);

watch(sortBy, () => {
  const sort = sortBy.value?.[0];

  router.replace({
    query: {
      "sort-by": sort?.key,
      "sort-desc": sort ? sort.order === "desc" : undefined,
    }
  }).catch(() => {});
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
    key: "displayedName",
    sortable: true
  },
  {
    title: "Admins",
    key: "admins",
    sortable: false
  },
  {
    title: "Number of runs",
    key: "runCount",
    align: "center",
    sortable: true
  },
  {
    title: "Latest store to product",
    key: "latestStoreToProduct",
    sortable: true
  },
  {
    title: "Actions",
    key: "actions",
    sortable: false
  },
]);

onMounted(() => {
  if (route.query["sort-by"]) {
    sortBy.value = [ {
      key: route.query["sort-by"],
      order: route.query["sort-desc"] === "true" ? "desc" : "asc"
    } ];
  }
  page.value = parseInt(route.query["page"]) || 1;
  itemsperpage.value = props.itemsPerPage;

  getTotalProducts();
  initializeComponent();
});

function getTotalProducts() {
  prodService.getClient().getProductCount(
    handleThriftError(count => {
      itemsLength.value = count;
    })
  );
}

function fetchProducts() {
  loading.value = true;

  const productNameFilter = productNameSearch.value
    ? `*${productNameSearch.value}*` : null;

  prodService.getClient().getProducts(
    null,
    productNameFilter,
    itemsperpage.value,
    itemsperpage.value * (page.value - 1),
    getSortingMode(),
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
      });

      loading.value = false;
    }));
}

function getSortingMode() {
  const sort = sortBy.value?.[0];
  const desc = sort?.order === "desc";

  switch (sort?.key) {
  case "displayedName":
    return desc ? ProductSortMode.NAMES_DESC : ProductSortMode.NAMES_ASC;
  case "runCount":
    return desc ? ProductSortMode.RUNS_DESC : ProductSortMode.RUNS_ASC;
  case "latestStoreToProduct":
    return desc
      ? ProductSortMode.LATEST_STORE_DESC
      : ProductSortMode.LATEST_STORE_ASC;
  default:
    // No column selected -> accessible-to-current-user products first.
    return ProductSortMode.ACCESSRIGHT;
  }
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
                headers.value.findIndex(h => h.key === "actions"), 1
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