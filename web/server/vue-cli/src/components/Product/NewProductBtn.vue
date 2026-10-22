<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="50%"
    title="New product"
    icon="mdi-plus"
    @confirm="save"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        id="new-product-btn"
        class="mr-2"
        v-bind="activatorProps"
        height="40"
        color="primary"
        variant="flat"
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
import { ref, watch } from "vue";
import { useStore } from "vuex";

import { handleThriftError, prodService } from "@cc-api";
import {
  DatabaseConnection,
  ProductConfiguration
} from "@cc/prod-types";

import { ADD_ERROR } from "@/store/mutations.type";
import ConfirmDialog from "@/components/ConfirmDialog";
import ProductConfigForm from "./ProductConfigForm";

defineProps({
  isSuperUser: { type: Boolean, default: false }
});
const emit = defineEmits([ "on-complete" ]);
const store = useStore();
const dialog = ref(false);
const isValid = ref(false);
const form = ref(null);

function newProductConfig() {
  return new ProductConfiguration({
    connection: new DatabaseConnection()
  });
}

const productConfig = ref(newProductConfig());

function resetForm() {
  productConfig.value = newProductConfig();
  form.value?.resetValidation?.();
}

// Clear the dialog state whenever it is closed (cancel or close button).
watch(dialog, isOpen => {
  if (!isOpen) resetForm();
});

async function save() {
  if (!await form.value.validate()) return;

  prodService.getClient().addProduct(productConfig.value,
    handleThriftError(() => {
      emit("on-complete", new ProductConfiguration(productConfig.value));

      dialog.value = false;
      resetForm();
    }, err => {
      store.commit(ADD_ERROR, {
        title: "Could not add product",
        message: err instanceof Error
          ? err.message
          : "Failed to add the product."
      });
    }));
}
</script>
