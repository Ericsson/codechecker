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

    <v-card>
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
              <edit-product
                :product-id="product.id"
              />
            </v-tab-item>
            <v-tab-item>
              TODO: Product permissions
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
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import EditProduct from "./EditProduct";

export default {
  name: "EditProductBtn",
  components: {
    EditProduct
  },
  props: {
    product: { type: Object, required: true }
  },
  data() {
    return {
      dialog: false,
      tab: null
    };
  },

  methods: {
    save() {}
  }
}
</script>
