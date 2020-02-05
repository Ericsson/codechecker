<template>
  <v-container fluid>
    <v-alert
      v-model="success"
      dismissible
      color="success"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-check"
    >
      Permission changes saved successfully!
    </v-alert>

    <v-alert
      v-model="error"
      dismissible
      color="error"
      border="left"
      elevation="2"
      colored-border
      icon="mdi-alert-outline"
    >
      Some permission changes could not be saved!
    </v-alert>

    <v-row justify="center">
      <v-col cols="auto">
        <product-user-permission
          :permissions="permissions"
          :auth-rights="userAuthRights"
          :bus="bus"
          :extra-params-json="extraParamsJSON"
          :is-group="false"
          :success.sync="success"
          :error.sync="error"
        />
      </v-col>
      <v-col cols="auto">
        <product-group-permission
          :permissions="permissions"
          :auth-rights="groupAuthRights"
          :bus="bus"
          :extra-params-json="extraParamsJSON"
          :is-group="true"
          :success.sync="success"
          :error.sync="error"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import PopulatePermissionsMixin from "./PopulatePermissions.mixin";
import ProductUserPermission from "./ProductUserPermission";
import ProductGroupPermission from "./ProductGroupPermission";

export default {
  name: "EditProductPermission",
  components: {
    ProductUserPermission,
    ProductGroupPermission
  },
  mixins: [ PopulatePermissionsMixin ],
  props: {
    product: { type: Object, required: true },
    bus: { type: Object, required: true }
  },

  data() {
    return {
      scope: "PRODUCT",
      extraParamsJSON: JSON.stringify({
        productID: this.product.id.toNumber()
      }),
      success: false,
      error: false
    };
  },

  mounted() {
    this.populatePermissions(this.scope, this.extraParamsJSON);
  }
}
</script>
