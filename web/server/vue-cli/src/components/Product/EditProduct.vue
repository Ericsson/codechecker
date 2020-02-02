<template>
  <v-form v-model="valid">
    <v-text-field
      v-model="productConfig.endpoint"
      :rules="rules.endpoint"
      label="URL endpoint"
      required
    />

    <v-text-field
      v-model="displayName"
      label="Display name"
    />

    <v-textarea
      v-model="description"
      label="Description"
    />

    <v-text-field
      v-model="productConfig.runLimit"
      label="Run limit"
    />

    <v-checkbox
      v-model="productConfig.isReviewStatusChangeDisabled"
      label="Disable review status change"
    />

    <v-divider />

    <v-radio-group v-model="dbConnection.engine">
      <v-radio
        label="SQLite"
        value="sqlite"
      />

      <v-radio
        label="PostgreSQL"
        value="postgresql"
      />
    </v-radio-group>

    <div
      v-if="dbConnection.engine == 'sqlite'"
    >
      <v-text-field
        v-model="dbConnection.database"
        label="Database file"
      />
    </div>

    <div
      v-if="dbConnection.engine == 'postgresql'"
    >
      <v-text-field
        v-model="dbConnection.host"
        label="Server address"
      />

      <v-text-field
        v-model="dbConnection.port"
        label="Port"
      />

      <v-text-field
        v-model="dbConnection.username"
        label="User name"
      />

      <v-text-field
        v-model="dbConnection.password"
        label="Password"
      />

      <v-text-field
        v-model="dbConnection.database"
        label="Database name"
      />
    </div>
  </v-form>
</template>

<script>
import {
  ProductConfiguration,
  DatabaseConnection
} from "@cc/prod-types";

import { prodService } from "@cc-api";

export default {
  name: "EditProduct",
  props: {
    productId: { type: [ Number, Object ], required: true }
  },
  data() {
    return {
      productConfig: new ProductConfiguration({
        connection: new DatabaseConnection()
      }),
      rules: {
        endpoint: [
          v => !!v || "Endpoint is required"
        ]
      },
      valid: false
    };
  },

  computed: {
    dbConnection() {
      return this.productConfig.connection;
    },
    description: {
      get() {
        return window.atob(this.productConfig.description_b64);
      },
      set(value) {
        this.productConfig.description_b64 = window.btoa(value);
      }
    },
    displayName: {
      get() {
        return window.atob(this.productConfig.displayedName_b64);
      },
      set(value) {
        this.productConfig.displayedName_b64 = window.btoa(value);
      }
    }
  },

  mounted() {
    prodService.getClient().getProductConfiguration(this.productId,
    (err, config) => {
      this.productConfig = config;
    });
  }
}
</script>
