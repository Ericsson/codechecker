<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    title="Confirm deletion of product"
    @confirm="confirmDelete"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        class="remove-btn"
        icon="mdi-trash-can-outline"
        color="error"
        variant="tonal"
        size="x-small"
      />
    </template>

    <template v-slot:content>
      <p>
        You have selected to delete <b>{{ product.endpoint }}</b>
        product!
      </p>
      <p>
        Deleting a product <b>will</b> remove product-specific
        configuration, such as access control and authorisation settings,
        and <b>will</b> disconnect the database from the server.
      </p>
      <p>
        Analysis results stored in the database <b>will NOT</b> be lost!
      </p>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";
import { handleThriftError, prodService } from "@cc-api";

const props = defineProps({
  product: { type: Object, required: true }
});

const emit = defineEmits([ "on-complete" ]);

const dialog = ref(false);

function confirmDelete() {
  prodService.getClient().removeProduct(props.product.id,
    handleThriftError(success => {
      if (success) {
        emit("on-complete", props.product);
      }
    }));
}
</script>
