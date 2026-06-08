<template>
  <v-form
    ref="form"
    v-model="valid"
  >
    <v-text-field
      v-if="isSuperUser"
      v-model="endpoint"
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
      v-model="runLimit"
      type="number"
      label="Run limit"
      name="run-limit"
      prepend-icon="mdi-speedometer"
      :rules="rules.runLimit"
    />

    <v-row
      class="ma-0"
    >
      <v-text-field
        v-if="isSuperUser"
        v-model="reportLimit"
        :value="productConfig.reportLimit"
        type="number"
        label="Report limit"
        name="report-limit"
        prepend-icon="mdi-close-octagon"
        :rules="rules.runLimit"
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
        prepend-icon="mdi-file-eye-outline"
        name="confidentiality"
        :items="confidentialityItems"
      />

      <tooltip-help-icon>
        Classification and handling of source code confidentiality.
      </tooltip-help-icon>
    </v-row>

    <v-checkbox
      v-model="isReviewStatusChangeDisabled"
      label="Disable review status change"
      name="disable-review-status-change"
    />

    <div
      v-if="isSuperUser"
    >
      <v-divider />

      <v-radio-group
        v-model="dbEngine"
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
          v-model="dbDatabase"
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
          v-model="dbHost"
          label="Server address*"
          name="db-host"
          prepend-icon="mdi-protocol"
          :rules="rules.dbHost"
          required
        />

        <v-text-field
          v-model="dbPort"
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
          v-model="dbDatabase"
          label="Database name*"
          name="db-name"
          prepend-icon="mdi-database"
          :rules="rules.dbName"
        />
      </div>
    </div>
  </v-form>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref
} from "vue";

import { useConfidentiality } from "@/composables/useConfidentiality";

import TooltipHelpIcon from "@/components/TooltipHelpIcon";
import { Confidentiality } from "@cc/prod-types";

const props = defineProps({
  productConfig: { type: Object, required: true },
  isValid: { type: Boolean, default: false },
  isSuperUser: { type: Boolean, default: false }
});

const emit = defineEmits([ "update:is-valid", "update:productConfig" ]);

const form = ref(null);

const {
  confidentialities,
  confidentialityFromCodeToString,
  confidentialityFromStringToCode 
} = useConfidentiality();

const rules = ref({
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
  ],
  reportLimit: [
    v => (!v || !!v && !isNaN(parseInt(v))) || "Number is required"
  ]
});

const confidentialityItems = computed(() => {
  return confidentialities();
});

const confidentialityString = computed({
  get() {
    return confidentialityFromCodeToString(
      props.productConfig.confidentiality
    );
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.confidentiality = confidentialityFromStringToCode(value);
    emit("update:productConfig", updated);
  }
});

const valid = computed({
  get() {
    return props.isValid;
  },

  set(value) {
    emit("update:is-valid", value);
  }
});

const dbConnection = computed(() => {
  return props.productConfig.connection;
});

const dbUserName = computed({
  get() {
    if (!props.productConfig.connection.username_b64) return "";

    return window.atob(props.productConfig.connection.username_b64);
  },

  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection };
    updated.connection.username_b64 = value.length ? window.btoa(value) : null;
    emit("update:productConfig", updated);
  }
});

const dbPassword = computed({
  get() {
    if (!props.productConfig.connection.password_b64) return "";

    return window.atob(props.productConfig.connection.password_b64);
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection };
    updated.connection.password_b64 = value.length ? window.btoa(value) : null;
    emit("update:productConfig", updated);
  }
});

const endpoint = computed({
  get() {
    return props.productConfig.endpoint;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.endpoint = value;
    emit("update:productConfig", updated);
  }
});

const displayName = computed({
  get() {
    if (!props.productConfig.displayedName_b64) return "";

    return window.atob(props.productConfig.displayedName_b64);
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.displayedName_b64 = value.length ? window.btoa(value) : null;
    emit("update:productConfig", updated);
  }
});

const description = computed({
  get() {
    if (!props.productConfig.description_b64) return "";

    return window.atob(props.productConfig.description_b64);
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.description_b64 = value.length ? window.btoa(value) : null;
    emit("update:productConfig", updated);
  }
});

const runLimit = computed({
  get() {
    return props.productConfig.runLimit;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.runLimit = value;
    emit("update:productConfig", updated);
  }
});

const reportLimit = computed({
  get() {
    return props.productConfig.reportLimit;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.reportLimit = value;
    emit("update:productConfig", updated);
  }
});

const dbEngine = computed({
  get() {
    return props.productConfig.connection.engine;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection, engine: value };
    emit("update:productConfig", updated);
  }
});

const dbDatabase = computed({
  get() {
    return props.productConfig.connection.database;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection, database: value };
    emit("update:productConfig", updated);
  }
});

const dbHost = computed({
  get() {
    return props.productConfig.connection.host;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection, host: value };
    emit("update:productConfig", updated);
  }
});

const dbPort = computed({
  get() {
    return props.productConfig.connection.port;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.connection = { ...updated.connection, port: value };
    emit("update:productConfig", updated);
  }
});

const isReviewStatusChangeDisabled = computed({
  get() {
    return props.productConfig.isReviewStatusChangeDisabled;
  },
  set(value) {
    const updated = { ...props.productConfig };
    updated.isReviewStatusChangeDisabled = value;
    emit("update:productConfig", updated);
  }
});

onMounted(() => {
  if (!props.productConfig.confidentiality) {
    const updated = { ...props.productConfig };
    updated.confidentiality = Confidentiality.CONFIDENTIAL;
    emit("update:productConfig", updated);
  }
});

async function validate() {
  const { valid } = await form.value.validate();
  return valid;
}

defineExpose({
  validate
});
</script>
