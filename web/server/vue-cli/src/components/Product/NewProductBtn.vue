<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="50%"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        v-on="on"
      >
        New product
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        New product

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <product-config-form
            :is-valid.sync="isValid"
            :product-config="productConfig"
          />
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
import { prodService } from "@cc-api";
import {
  ProductConfiguration,
  DatabaseConnection
} from "@cc/prod-types";

import ProductConfigForm from "./ProductConfigForm";

export default {
  name: "NewProductBtn",
  components: {
    ProductConfigForm
  },
  data() {
    return {
      dialog: false,
      productConfig: new ProductConfiguration({
        connection: new DatabaseConnection()
      }),
      isValid: false
    };
  },
  methods: {
    save() {
      prodService.getClient().addProduct(this.productConfig, (/* err */) => {
        this.$emit("on-complete", new ProductConfiguration(this.productConfig));

        this.dialog = false;
        this.productConfig = new ProductConfiguration({
          connection: new DatabaseConnection()
        });
      });
    }
  }
}
</script>
