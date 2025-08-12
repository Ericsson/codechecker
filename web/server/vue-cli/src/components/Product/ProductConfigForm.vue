<template>
  <v-form
    ref="form"
    v-model="valid"
  >
    <v-text-field
      v-model="productConfig.endpoint"
      :rules="rules.endpoint"
      label="URL endpoint*"
      name="endpoint"
      prepend-inner-icon="mdi-card-account-details-outline"
      required
    />

    <v-text-field
      v-model="displayName"
      label="Display name"
      name="display-name"
      prepend-inner-icon="mdi-television"
    />

    <v-textarea
      v-model="description"
      label="Description"
      name="description"
      prepend-inner-icon="mdi-text"
      rows="1"
    />

    <v-text-field
      :model-value="productConfig.runLimit"
      type="number"
      label="Run limit"
      name="run-limit"
      prepend-inner-icon="mdi-speedometer"
      :rules="rules.runLimit"
      @update:modelValue="v => productConfig.runLimit = v || null"
    />

    <v-row
      class="ma-0"
    >
      <v-text-field
        :model-value="productConfig.reportLimit"
        type="number"
        label="Report limit"
        name="report-limit"
        prepend-inner-icon="mdi-close-octagon"
        :rules="rules.runLimit"
        @update:modelValue="v => productConfig.reportLimit = v || null"
      />

      <tooltip-help-icon>
        The maximum number of reports allowed to
        store in one run, if exceeded, the store
        action will be rejected.
      </tooltip-help-icon>
    </v-row>

    <v-row
      class="ma-0"
    >
      <v-select
        v-model="confidentialityString"
        label="Information Classification"
        class="select-confidentiality"
        prepend-inner-icon="mdi-file-eye-outline"
        name="confidentiality"
        :items="confidentialityItems"
        item-title="title"
        item-value="value"
      >
        <template v-slot:selection="{ item }">
          <select-confidentiality-item :value="item.raw || item" />
        </template>
        <template v-slot:item="{ item }">
          <select-confidentiality-item :value="item.raw || item" />
        </template>
      </v-select>

      <tooltip-help-icon>
        Classification and handling of source code confidentiality.
      </tooltip-help-icon>
    </v-row>

    <v-checkbox
      v-model="productConfig.isReviewStatusChangeDisabled"
      label="Disable review status change"
      name="disable-review-status-change"
    />

    <div
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
          prepend-inner-icon="mdi-database"
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
          prepend-inner-icon="mdi-protocol"
          :rules="rules.dbHost"
          required
        />

        <v-text-field
          v-model="dbConnection.port"
          label="Port*"
          name="db-port"
          prepend-inner-icon="mdi-map-marker"
          :rules="rules.dbPort"
          required
        />

        <v-text-field
          v-model="dbUserName"
          label="User name*"
          name="db-username"
          prepend-inner-icon="mdi-account-outline"
          autocomplete="new-password"
          :rules="rules.dbUserName"
          required
        />

        <v-text-field
          v-model="dbPassword"
          type="password"
          label="Password"
          name="db-password"
          prepend-inner-icon="mdi-lock-outline"
          autocomplete="new-password"
        />

        <v-text-field
          v-model="dbConnection.database"
          label="Database name*"
          name="db-name"
          prepend-inner-icon="mdi-database"
          :rules="rules.dbName"
        />
      </div>
    </div>
  </v-form>
</template>

<script>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import SelectConfidentialityItem from "./SelectConfidentialityItem.vue";
import { ConfidentialityMixin } from "@/mixins";
import { Confidentiality } from "@cc/prod-types";

export default {
  name: "EditProduct",
  components: {
    TooltipHelpIcon, SelectConfidentialityItem
  },
  mixins: [ ConfidentialityMixin ],
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
        dbUserName: [
          v => !!v || "Database user name is required"
        ],
        engine: [
          v => !!v || "Engine is required"
        ],
        runLimit: [
          v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
        ],
        reportLimit: [
          v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
        ]
      },
    };
  },

  computed: {
    confidentialityItems() {
      return this.confidentialities();
    },

    confidentialityString: {
      get() {
        return this.confidentialityFromCodeToString(
          this.productConfig.confidentiality
        );
      },
      set(value) {
        this.productConfig.confidentiality =
          this.confidentialityFromStringToCode(value);
      }
    },

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
    },
  },

  created () {
    if (!this.productConfig.confidentiality) {
      this.productConfig.confidentiality = Confidentiality.CONFIDENTIAL;
    }
  },
  methods: {
    validate() {
      return this.$refs.form.validate();
    }
  }
};
</script>
