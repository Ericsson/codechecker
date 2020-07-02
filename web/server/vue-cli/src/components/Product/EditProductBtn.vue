<template>
  <confirm-dialog
    v-model="dialog"
    max-width="80%"
    :loading="loading"
    @confirm="save"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        class="edit-btn"
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
      <v-alert
        v-model="success"
        dismissible
        color="success"
        border="left"
        elevation="2"
        colored-border
        icon="mdi-check"
      >
        Successfully saved.
      </v-alert>

      <v-alert
        v-model="error"
        dismissible
        color="error"
        border="left"
        elevation="2"
        colored-border
        icon="mdi-alert-outline"
      >
        Failed to save product changes.
      </v-alert>

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
              :is-super-user="isSuperUser"
              :product-config="productConfig"
            />
          </v-container>
        </v-tab-item>
        <v-tab-item>
          <edit-product-permission
            :product="product"
            :bus="bus"
            :success.sync="success"
            :error.sync="error"
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
    isSuperUser: { type: Boolean, default: false }
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
      success: false,
      error: false,
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
        handleThriftError(success => {
          if (!success) {
            this.error = true;
            return;
          }

          this.success = true;
          this.$emit("on-complete",
            new ProductConfiguration(this.productConfig));
        }, () => {
          this.error = true;
        }));

      // Save permissions.
      this.bus.$emit("save");
    }
  }
};
</script>
