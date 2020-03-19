<template>
  <v-form v-model="valid">
    <v-text-field
      v-if="isSuperUser"
      v-model="productConfig.endpoint"
      :rules="rules.endpoint"
      label="URL endpoint*"
      prepend-icon="mdi-account-card-details-outline"
      required
    />

    <v-text-field
      v-model="displayName"
      label="Display name"
      prepend-icon="mdi-television"
    />

    <v-textarea
      v-model="description"
      label="Description"
      prepend-icon="mdi-text"
      rows="1"
    />

    <v-text-field
      v-if="isSuperUser"
      v-model="productConfig.runLimit"
      label="Run limit"
      prepend-icon="mdi-speedometer"
    />

    <v-checkbox
      v-model="productConfig.isReviewStatusChangeDisabled"
      label="Disable review status change"
    />

    <div
      v-if="isSuperUser"
    >
      <v-divider />

      <v-radio-group
        v-model="dbConnection.engine"
        :rules="rules.engine"
      >
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
          label="Database file*"
          prepend-icon="mdi-database"
          :rules="rules.dbFile"
        />
      </div>

      <div
        v-if="dbConnection.engine == 'postgresql'"
      >
        <v-text-field
          v-model="dbConnection.host"
          label="Server address"
          prepend-icon="mdi-protocol"
        />

        <v-text-field
          v-model="dbConnection.port"
          label="Port"
          prepend-icon="mdi-map-marker"
        />

        <v-text-field
          v-model="dbConnection.username"
          label="User name"
          prepend-icon="mdi-account-outline"
        />

        <v-text-field
          v-model="dbConnection.password"
          label="Password"
          prepend-icon="mdi-lock-outline"
        />

        <v-text-field
          v-model="dbConnection.database"
          label="Database name*"
          prepend-icon="mdi-database"
          :rules="rules.dbName"
        />
      </div>
    </div>
  </v-form>
</template>

<script>
export default {
  name: "EditProduct",
  props: {
    productConfig: { type: Object, required: true },
    isValid: { type: Boolean, default: false },
    isSuperUser: { type: Boolean, default: false }
  },
  data() {
    return {
      rules: {
        endpoint: [
          v => !!v || "Endpoint is required"
        ],
        dbFile: [
          v => !!v || "Database file is required"
        ],
        dbName: [
          v => !!v || "Database name is required"
        ],
        engine: [
          v => !!v || "Engine is required"
        ]
      },
    };
  },

  computed: {
    valid: {
      get() {
        return this.isValid;
      },
      set(value) {
        this.$emit("update:is-valid", value);
      }
    },

    dbConnection() {
      return this.productConfig.connection;
    },
    description: {
      get() {
        if (!this.productConfig.description_b64) return "";

        return window.atob(this.productConfig.description_b64);
      },
      set(value) {
        this.productConfig.description_b64 =
          value.length ? window.btoa(value) : null;
      }
    },
    displayName: {
      get() {
        if (!this.productConfig.displayedName_b64) return "";

        return window.atob(this.productConfig.displayedName_b64);
      },
      set(value) {
        this.productConfig.displayedName_b64 =
          value.length ? window.btoa(value) : null;
      }
    }
  }
};
</script>
