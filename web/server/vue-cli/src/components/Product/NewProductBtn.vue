<template>
  <confirm-dialog
    v-model="dialog"
    max-width="50%"
    @confirm="save"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        id="new-product-btn"
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
        ref="form"
        :is-valid.sync="isValid"
        :is-super-user="isSuperUser"
        :product-config="productConfig"
      />
    </template>
  </confirm-dialog>
</template>

<script>
import { handleThriftError, prodService } from "@cc-api";
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
  props: {
    isSuperUser: { type: Boolean, default: false }
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
      if (!this.$refs.form.validate()) return;

      prodService.getClient().addProduct(this.productConfig,
        handleThriftError(() => {
          this.$emit("on-complete",
            new ProductConfiguration(this.productConfig));

          this.dialog = false;
          this.productConfig = new ProductConfiguration({
            connection: new DatabaseConnection()
          });
        }));
    }
  }
};
</script>
