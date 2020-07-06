<template>
  <confirm-dialog
    v-model="dialog"
    max-width="600px"
    cancel-btn-color="primary"
    confirm-btn-label="Remove"
    confirm-btn-color="error"
    @confirm="confirmDelete"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        class="remove-btn"
        icon
        color="error"
        v-on="on"
      >
        <v-icon>mdi-trash-can-outline</v-icon>
      </v-btn>
    </template>

    <template v-slot:title>
      Confirm deletion of product
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
  </confirm-dialog>
</template>

<script>
import { handleThriftError, prodService } from "@cc-api";
import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  name: "DeleteProductBtn",
  components: {
    ConfirmDialog
  },
  props: {
    product: { type: Object, required: true }
  },

  data() {
    return {
      dialog: false
    };
  },

  methods: {
    confirmDelete() {
      prodService.getClient().removeProduct(this.product.id,
        handleThriftError(success => {
          if (success) {
            this.$emit("on-complete", this.product);
          }
        }));
    }
  }
};
</script>
