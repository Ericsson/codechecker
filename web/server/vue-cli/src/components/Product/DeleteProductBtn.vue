<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        icon
        color="error"
        v-on="on"
      >
        <v-icon>mdi-trash-can-outline</v-icon>
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Confirm deletion of product

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
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
          color="error"
          text
          @click="confirmDelete"
        >
          Remove
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { prodService } from "@cc-api";

export default {
  name: "DeleteProductBtn",
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
      (/* error, success */) => {
        this.$emit("on-complete", this.product);
      });
    }
  }
};
</script>
