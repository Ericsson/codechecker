<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="50%"
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

    <v-card
      v-if="loading"
      color="primary"
      dark
    >
      <v-card-text>
        Loading...
        <v-progress-linear
          indeterminate
          color="white"
          class="mb-0"
        />
      </v-card-text>
    </v-card>

    <v-card v-else>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Edit product

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
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
              <product-config-form
                :is-valid.sync="isValid"
                :product-config="productConfig"
              />
            </v-tab-item>
            <v-tab-item>
              <edit-product-permission
                :product="product"
                :bus="bus"
              />
            </v-tab-item>
          </v-tabs-items>
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          text
          :disabled="!isValid"
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import Vue from "vue";

import { prodService } from "@cc-api";
import {
  ProductConfiguration,
  DatabaseConnection
} from "@cc/prod-types";

import EditProductPermission from "./Permission/EditProductPermission";
import ProductConfigForm from "./ProductConfigForm";

export default {
  name: "EditProductBtn",
  components: {
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
      (err, config) => {
        this.productConfig = config;
        this.loading = false;
      });
    }
  },

  methods: {
    save() {
      prodService.getClient().editProduct(this.product.id, this.productConfig,
      (/* err */) => {
        this.$emit("on-complete", new ProductConfiguration(this.productConfig));
      });

      // Save permissions.
      this.bus.$emit("save");
    }
  }
}
</script>
