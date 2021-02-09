<template>
  <v-list-item
    class="pa-0"
    two-line
  >
    <v-list-item-avatar class="my-1">
      <v-avatar
        :color="strToColor(product.endpoint)"
        size="48"
        class="my-1"
      >
        <span class="white--text headline">
          {{ product.endpoint | productIconName }}
        </span>
      </v-avatar>
    </v-list-item-avatar>

    <v-list-item-content>
      <v-list-item-title>
        <span
          v-if="product.databaseStatus !== DBStatus.OK || !product.accessible"
          :style="{ 'text-decoration': 'line-through' }"
        >
          {{ product.displayedName }}
        </span>

        <router-link
          v-else
          :to="{ name: 'runs', params: { endpoint: product.endpoint } }"
        >
          {{ product.displayedName }}
        </router-link>

        <span
          v-if="!product.accessible"
          color="grey--text"
        >
          <v-icon>mdi-alert-outline</v-icon>
          You do not have access to this product!
        </span>

        <span
          v-else-if="product.databaseStatus !== DBStatus.OK"
          class="error--text"
        >
          <v-icon>mdi-alert-outline</v-icon>
          {{ dbStatusFromCodeToString(product.databaseStatus) }}
          <span
            v-if="product.databaseStatus === DBStatus.SCHEMA_MISMATCH_OK ||
              product.databaseStatus === DBStatus.SCHEMA_MISSING"
          >
            Use <kbd>CodeChecker server</kbd> command for schema
            upgrade/initialization.
          </span>
        </span>
      </v-list-item-title>

      <v-list-item-subtitle>
        {{ product.description }}
      </v-list-item-subtitle>

      <v-list-item-subtitle
        v-if="product.databaseStatus === DBStatus.OK && product.accessible"
      >
        <span
          v-for="link in links"
          :key="link.name"
        >
          <v-btn
            :to="{
              name: link.name,
              params: { endpoint: product.endpoint },
              query: link.query || {}
            }"
            :title="link.title"
            :color="link.color"
            x-small
            text
            icon
          >
            <v-icon>{{ link.icon }}</v-icon>
          </v-btn>

          <v-divider
            v-if="link.divider"
            class="mx-2 d-inline"
            inset
            vertical
          />
        </span>
      </v-list-item-subtitle>
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import { DBStatus } from "@cc/shared-types";
import { StrToColorMixin } from "@/mixins";
import { defaultReportFilterValues } from "@/components/Report/ReportFilter";

export default {
  name: "ProductNameColumn",
  filters: {
    productIconName: function (endpoint) {
      if (!endpoint) return "";

      return endpoint.charAt(0).toUpperCase();
    }
  },
  mixins: [ StrToColorMixin ],
  props: {
    product: { type: Object, required: true }
  },
  data() {
    return {
      DBStatus,
      links: [
        { name: "runs", title: "Show runs", color: "primary",
          icon: "mdi-run-fast", divider: true },
        { name: "reports", title: "Show reports", color: "rgb(236, 118, 114)",
          icon: "mdi-bug", query: defaultReportFilterValues, divider: true },
        { name: "statistics", title: "Show statistics", color: "green",
          icon: "mdi-chart-line", query: defaultReportFilterValues },
      ]
    };
  },
  methods: {
    dbStatusFromCodeToString(dbStatus) {
      switch (parseInt(dbStatus)) {
      case DBStatus.OK:
        return "Database is up to date.";
      case DBStatus.MISSING:
        return "Database is missing.";
      case DBStatus.FAILED_TO_CONNECT:
        return "Failed to connect to the database.";
      case DBStatus.SCHEMA_MISMATCH_OK:
        return "Schema mismatch: migration is possible.";
      case DBStatus.SCHEMA_MISMATCH_NO:
        return "Schema mismatch: migration not available.";
      case DBStatus.SCHEMA_MISSING:
        return "Schema is missing.";
      case DBStatus.SCHEMA_INIT_ERROR:
        return "Schema initialization error.";
      default:
        console.warn("Non existing database status code: ", dbStatus);
        return "N/A";
      }
    },
  }
};
</script>
