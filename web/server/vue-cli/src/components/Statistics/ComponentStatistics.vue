<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h3 class="title primary--text">
          <v-btn
            color="primary"
            outlined
            @click="downloadCSV"
          >
            Export CSV
          </v-btn>

          <v-btn
            icon
            title="Reload statistics"
            color="primary"
            @click="fetchStatistics"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </h3>

        <component-statistics-table
          :items="statistics"
          :loading="loading"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import { ReviewStatus } from "@cc/report-server-types";
import { ToCSV } from "@/mixins";

import BaseStatistics from "./BaseStatistics";
import ComponentStatisticsTable from "./ComponentStatisticsTable";
import {
  getComponentStatistics,
  getComponents,
  resultToNumber
} from "./StatisticsHelper";

export default {
  name: "ComponentStatistics",
  components: {
    ComponentStatisticsTable
  },
  mixins: [ BaseStatistics, ToCSV ],

  props: {
    namespace: { type: String, required: true }
  },

  data() {
    return {
      ReviewStatus,
      loading: false,
      statistics: []
    };
  },

  computed: {
    ...mapState({
      runIds(state, getters) {
        return getters[`${this.namespace}/getRunIds`];
      },
      reportFilter(state, getters) {
        return getters[`${this.namespace}/getReportFilter`];
      }
    })
  },

  methods: {
    downloadCSV() {
      const data = [
        [
          "Component", "All reports", "Unreviewed", "Confirmed bug",
          "False positive", "Intentional"
        ],
        ...this.statistics.map(stat => {
          return [
            stat.name, stat.reports, stat.unreviewed, stat.confirmed,
            stat.falsePositive, stat.intentional
          ];
        })
      ];

      this.toCSV(data, "codechecker_component_statistics.csv");
    },

    async fetchStatistics() {
      this.loading = true;
      this.statistics = [];

      const components = await getComponents();
      this.statistics = components.map(c => ({
        name: c.name,
        value: c.value
      }));

      const queries = components.map(async component => {
        const res = await getComponentStatistics(component.name);
        const idx = this.statistics.findIndex(s => s.name === component.name);
        this.statistics[idx] = {
          name          : component.name,
          value         : component.value,
          reports       : resultToNumber(res[1]),
          unreviewed    : resultToNumber(res[1]),
          confirmed     : resultToNumber(res[2]),
          falsePositive : resultToNumber(res[3]),
          intentional   : resultToNumber(res[4]),
          loading       : false,
          checkerStatistics: null
        };

        this.statistics = [ ...this.statistics ];

        return this.statistics[idx];
      });

      Promise.all(queries).then(statistics => {
        this.statistics = statistics;
        this.loading = false;
      });
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-data-table__expanded__content .v-card {
  padding: 10px;
}
</style>
