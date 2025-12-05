<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="50%"
    title="New product"
    @confirm="save"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        id="new-product-btn"
        color="primary"
        class="mr-2"
        variant="tonal"
      >
        <template v-slot:prepend>
          <v-icon>mdi-plus</v-icon>
        </template>
        New product
      </v-btn>
    </template>

    <template v-slot:content>
      <ProductConfigForm
        ref="form"
        v-model="isValid"
        v-model:product-config="productConfig"
        :is-super-user="isSuperUser"
      />
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref } from "vue";

import { handleThriftError, prodService } from "@cc-api";
import {
  DatabaseConnection,
  ProductConfiguration
} from "@cc/prod-types";

import ConfirmDialog from "@/components/ConfirmDialog";
import ProductConfigForm from "./ProductConfigForm";

defineProps({
  isSuperUser: { type: Boolean, default: false }
});
const emit = defineEmits([ "on-complete" ]);
const dialog = ref(false);
const isValid = ref(false);
const form = ref(null);
const productConfig = ref(new ProductConfiguration({
  connection: new DatabaseConnection()
}));

function save() {
  if (!form.value.validate()) return;

  prodService.getClient().addProduct(productConfig.value,
    handleThriftError(() => {
      emit("on-complete", new ProductConfiguration(productConfig.value));

      dialog.value = false;
      productConfig.value = new ProductConfiguration({
        connection: new DatabaseConnection()
      });
    }));
}
</script>
