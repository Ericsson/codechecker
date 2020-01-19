<template>
  <select-option
    title="Severity"
    :items="items"
    :fetch-items="fetchItems"
    :loading="loading"
    :selected-items="selectedItems"
  >
    <template v-slot:icon="{ item }">
      <severity-icon :status="item.id" />
    </template>
  </select-option>
</template>

<script>
import { ccService } from '@cc-api';

import { Severity } from "@cc/report-server-types";
import { SeverityIcon } from "@/components/icons";

import SelectOption from './SelectOption/SelectOption';

function severityFromCodeToString(severity) {
  switch (severity) {
    case Severity.UNSPECIFIED:
      return 'Unspecified';
    case Severity.STYLE:
      return 'Style';
    case Severity.LOW:
      return 'Low';
    case Severity.MEDIUM:
      return 'Medium';
    case Severity.HIGH:
      return 'High';
    case Severity.CRITICAL:
      return 'Critical';
    default:
      return '';
  }
}

function severityFromStringToCode(severity) {
  switch (severity.toLowerCase()) {
    case 'unspecified':
      return Severity.UNSPECIFIED;
    case 'style':
      return Severity.STYLE;
    case 'low':
      return Severity.LOW;
    case 'medium':
      return Severity.MEDIUM;
    case 'high':
      return Severity.HIGH;
    case 'critical':
      return Severity.CRITICAL;
    default:
      return -1;
  }
}

export default {
  name: 'SeverityFilter',
  components: {
    SelectOption,
    SeverityIcon
  },

  props: {
    reportFilter: { type: Object, required: true }
  },

  data() {
    return {
      id: "severity",
      selectedItems: [],
      items: [],
      loading: false
    };
  },

  watch: {
    selectedItems() {
      this.updateUrl();
      this.updateReportFilter();
    }
  },

  created() {
    this.initByUrl();
  },

  methods: {
    encodeValue(severityId) {
      return severityFromCodeToString(severityId);
    },

    decodeValue(severityName) {
      return severityFromStringToCode(severityName)
    },

    getUrlState() {
      return {
        [this.id]: this.selectedItems.map((item) => this.encodeValue(item.id))
      };
    },

    initByUrl() {
      const state = [].concat(this.$route.query[this.id] || []);
      if (state.length) {
        this.selectedItems = state.map((s) => {
          return {
            id: this.decodeValue(s),
            title: s,
            count: "N/A"
          };
        });

        this.fetchItems();
      }
    },

    updateUrl() {
      const state = this.getUrlState();
      const queryParams = Object.assign({}, this.$route.query, state);
      this.$router.replace({ query: queryParams }).catch(() => {});
    },

    updateReportFilter() {
      this.reportFilter.severity = this.selectedItems.map(item => item.id);
    },

    updateSelectedItems() {
      this.selectedItems.forEach((selectedItem) => {
        const item = this.items.find((i) => i.id === selectedItem.id);
        if (item) {
          selectedItem.count = item.count;
        }
      });
    },

    fetchItems() {
      this.loading = true;

      const runIds = null;
      const reportFilter = null;
      const cmpData = null;

      ccService.getClient().getSeverityCounts(runIds, reportFilter, cmpData,
      (err, res) => {
        this.items = Object.keys(Severity).map(status => {
          const severityId = Severity[status];
          return {
            id: severityId,
            title: severityFromCodeToString(severityId),
            count: res[severityId] !== undefined ? res[severityId] : 0
          };
        });
        this.updateSelectedItems();
        this.loading = false;
      });
    }
  }
}
</script>
