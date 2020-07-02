<template>
  <v-container fluid>
    <v-row justify="center">
      <v-col cols="auto">
        <product-user-permission
          :permissions="permissions"
          :auth-rights="userAuthRights"
          :bus="bus"
          :extra-params-json="extraParamsJSON"
          :is-group="false"
          :success="success"
          :error="error"
          @update:success="(success) => $emit('update:success', success)"
          @update:error="(error) => $emit('update:error', error)"
        />
      </v-col>
      <v-col cols="auto">
        <product-group-permission
          :permissions="permissions"
          :auth-rights="groupAuthRights"
          :bus="bus"
          :extra-params-json="extraParamsJSON"
          :is-group="true"
          :success="success"
          :error="error"
          @update:success="(success) => $emit('update:success', success)"
          @update:error="(error) => $emit('update:error', error)"
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
    bus: { type: Object, required: true },
    success: { type: Boolean, default: false },
    error: { type: Boolean, default: false }
  },

  data() {
    return {
      scope: "PRODUCT",
      extraParamsJSON: JSON.stringify({
        productID: this.product.id.toNumber()
      })
    };
  },

  mounted() {
    this.populatePermissions(this.scope, this.extraParamsJSON);
  }
};
</script>
