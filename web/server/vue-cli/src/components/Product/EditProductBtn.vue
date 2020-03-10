<template>
  <confirm-dialog
    v-model="dialog"
    max-width="80%"
    :loading="loading"
    @confirm="save"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        icon
        color="primary"
        v-on="on"
      >
        <v-icon>mdi-pencil</v-icon>
      </v-btn>
    </template>

    <template v-slot:title>
      Edit product
    </template>

    <template v-slot:content>
      <v-tabs
        v-model="tab"
        background-color="transparent"
        color="basil"
        grow
      >
        <v-tab>
          Edit
        </v-tab>
        <v-tab>
          Permissions
        </v-tab>
      </v-tabs>

      <v-tabs-items
        v-model="tab"
      >
        <v-tab-item>
          <v-container fluid>
            <product-config-form
              :is-valid.sync="isValid"
              :product-config="productConfig"
            />
          </v-container>
        </v-tab-item>
        <v-tab-item>
          <edit-product-permission
            :product="product"
            :bus="bus"
          />
        </v-tab-item>
      </v-tabs-items>
    </template>
  </confirm-dialog>
</template>

<script>
import Vue from "vue";

import { handleThriftError, prodService } from "@cc-api";
import {
  DatabaseConnection,
  ProductConfiguration
} from "@cc/prod-types";

import ConfirmDialog from "@/components/ConfirmDialog";
import EditProductPermission from "./Permission/EditProductPermission";
import ProductConfigForm from "./ProductConfigForm";

export default {
  name: "EditProductBtn",
  components: {
    ConfirmDialog,
    EditProductPermission,
    ProductConfigForm
  },
  props: {
    product: { type: Object, required: true },
  },
  data() {
    return {
      dialog: false,
      productConfig: new ProductConfiguration({
        connection: new DatabaseConnection()
      }),
      tab: null,
      loading: false,
      isValid: false,
      bus: new Vue()
    };
  },
  watch: {
    dialog() {
      if (!this.dialog) return;

      this.loading = true;
      prodService.getClient().getProductConfiguration(this.product.id,
        handleThriftError(config => {
          this.productConfig = config;
          this.loading = false;
        }));
    }
  },

  methods: {
    save() {
      prodService.getClient().editProduct(this.product.id, this.productConfig,
        handleThriftError(() => {
          this.$emit("on-complete",
            new ProductConfiguration(this.productConfig));
        }));

      // Save permissions.
      this.bus.$emit("save");
    }
  }
};
</script>
