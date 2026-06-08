<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="80%"
    :loading="loading"
    title="Edit product"
    @confirm="save"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        class="edit-btn mr-2"
        icon="mdi-pencil"
        color="primary"
        size="x-small"
        variant="tonal"
      />
    </template>

    <template v-slot:content>
      <v-alert
        v-model="success"
        dismissible
        color="success"
        border="start"
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
        border="start"
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

      <v-window
        v-model="tab"
      >
        <v-window-item>
          <v-container fluid>
            <product-config-form
              v-model="isValid"
              v-model:product-config="productConfig"
              :is-super-user="isSuperUser"
            />
          </v-container>
        </v-window-item>
        <v-window-item>
          <EditProductPermission
            ref="editProductPermission"
            v-model:success="success"
            v-model:error="error"
            :product="product"
          />
        </v-window-item>
      </v-window>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref, watch } from "vue";

import { handleThriftError, prodService } from "@cc-api";
import {
  DatabaseConnection,
  ProductConfiguration
} from "@cc/prod-types";

import ConfirmDialog from "@/components/ConfirmDialog";
import EditProductPermission from "./Permission/EditProductPermission";
import ProductConfigForm from "./ProductConfigForm";

const props = defineProps({
  product: { type: Object, required: true },
  isSuperUser: { type: Boolean, default: false }
});
const emit = defineEmits([ "on-complete" ]);
const dialog = ref(false);
const tab = ref(null);
const loading = ref(false);
const isValid = ref(false);
const success = ref(false);
const error = ref(false);

const editProductPermission = ref(null);

const productConfig = ref(new ProductConfiguration({
  connection: new DatabaseConnection()
}));

watch(dialog, () => {
  if (!dialog.value) return;

  loading.value = true;
  prodService.getClient().getProductConfiguration(props.product.id,
    handleThriftError(_config => {
      productConfig.value = _config;
      loading.value = false;
    }));
});

function save() {
  prodService.getClient().editProduct(props.product.id, productConfig.value,
    handleThriftError(_success => {
      if (!_success) {
        error.value = true;
        return;
      }

      success.value = true;
      emit("on-complete",
        new ProductConfiguration(productConfig.value));
    }));

  // Save permissions.
  editProductPermission.value?.savePermissions();
}
</script>
