<template>
  <confirm-dialog
    v-model="dialog"
    max-width="50%"
    @confirm="save"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        v-on="on"
      >
        <v-icon left>
          mdi-plus
        </v-icon>
        New product
      </v-btn>
    </template>

    <template v-slot:title>
      New product
    </template>

    <template v-slot:content>
      <product-config-form
        :is-valid.sync="isValid"
        :product-config="productConfig"
      />
    </template>
  </confirm-dialog>
</template>

<script>
import { prodService } from "@cc-api";
import {
  DatabaseConnection,
  ProductConfiguration
} from "@cc/prod-types";

import ConfirmDialog from "@/components/ConfirmDialog";
import ProductConfigForm from "./ProductConfigForm";

export default {
  name: "NewProductBtn",
  components: {
    ConfirmDialog,
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
};
</script>
