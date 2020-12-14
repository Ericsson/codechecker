<template>
  <v-form
    ref="form"
    v-model="valid"
  >
    <v-text-field
      v-if="isSuperUser"
      v-model="productConfig.endpoint"
      :rules="rules.endpoint"
      label="URL endpoint*"
      name="endpoint"
      prepend-icon="mdi-card-account-details-outline"
      required
    />

    <v-text-field
      v-model="displayName"
      label="Display name"
      name="display-name"
      prepend-icon="mdi-television"
    />

    <v-textarea
      v-model="description"
      label="Description"
      name="description"
      prepend-icon="mdi-text"
      rows="1"
    />

    <v-text-field
      v-if="isSuperUser"
      :value="productConfig.runLimit"
      type="number"
      label="Run limit"
      name="run-limit"
      prepend-icon="mdi-speedometer"
      :rules="rules.runLimit"
      @input="productConfig.runLimit = $event || null"
    />

    <v-checkbox
      v-model="productConfig.isReviewStatusChangeDisabled"
      label="Disable review status change"
      name="disable-review-status-change"
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
          name="db-file"
          prepend-icon="mdi-database"
          :rules="rules.dbFile"
        />
      </div>

      <div
        v-if="dbConnection.engine == 'postgresql'"
      >
        <v-text-field
          v-model="dbConnection.host"
          label="Server address*"
          name="db-host"
          prepend-icon="mdi-protocol"
          :rules="rules.dbHost"
          required
        />

        <v-text-field
          v-model="dbConnection.port"
          label="Port*"
          name="db-port"
          prepend-icon="mdi-map-marker"
          :rules="rules.dbPort"
          required
        />

        <v-text-field
          v-model="dbUserName"
          label="User name*"
          name="db-username"
          prepend-icon="mdi-account-outline"
          autocomplete="new-password"
          :rules="rules.dbUserName"
          required
        />

        <v-text-field
          v-model="dbPassword"
          type="password"
          label="Password"
          name="db-password"
          prepend-icon="mdi-lock-outline"
          autocomplete="new-password"
        />

        <v-text-field
          v-model="dbConnection.database"
          label="Database name*"
          name="db-name"
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
        dbHost: [
          v => !!v || "Database host is required"
        ],
        dbPort: [
          v => !!v || "Database port is required"
        ],
        dbUser: [
          v => !!v || "Database user name is required"
        ],
        engine: [
          v => !!v || "Engine is required"
        ],
        runLimit: [
          v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
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

    dbUserName: {
      get() {
        if (!this.productConfig.connection.username_b64) return "";

        return window.atob(this.productConfig.connection.username_b64);
      },
      set(value) {
        this.productConfig.connection.username_b64 =
          value.length ? window.btoa(value) : null;
      }
    },

    dbPassword: {
      get() {
        if (!this.productConfig.connection.password_b64) return "";

        return window.atob(this.productConfig.connection.password_b64);
      },
      set(value) {
        this.productConfig.connection.password_b64 =
          value.length ? window.btoa(value) : null;
      }
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
  },

  methods: {
    validate() {
      return this.$refs.form.validate();
    }
  }
};
</script>
