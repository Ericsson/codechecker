<script>
import { Pie, mixins } from "vue-chartjs";
import { Severity } from "@cc/report-server-types";
import { SeverityMixin } from "@/mixins";

const { reactiveData } = mixins;

export default {
  name: "ComponentSeverityStatisticsChart",
  extends: Pie,
  mixins: [ reactiveData, SeverityMixin ],
  props: {
    statistics: { type: Array, required: true },
    loading: { type: Boolean, required: true }
  },
  data() {
    const severities = [
      Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW,
      Severity.STYLE, Severity.UNSPECIFIED
    ];

    const labels = severities.map(s => this.severityFromCodeToString(s));
    const colors = severities.map(s => this.severityFromCodeToColor(s));

    return {
      severities,
      options: {
        legend: {
          display: true,
          position: "bottom"
        },
        title: {
          display: true,
          text: "Report severities"
        },
        responsive: true,
        maintainAspectRatio: false
      },
      chartData: {
        labels: labels,
        datasets: [
          {
            data: [],
            backgroundColor: colors
          }
        ]
      }
    };
  },
  watch: {
    loading() {
      if (this.loading) return;

      this.chartData.datasets[0].data = this.statistics.reduce((acc, curr) => {
        this.chartData.labels.forEach((s, idx) => {
          acc[idx] += curr[s.toLowerCase()].count;
        });

        return acc;
      }, new Array(this.chartData.labels.length).fill(0));
      this.renderChart(this.chartData, this.options);
    }
  },
  mounted() {
    this.renderChart(this.chartData, this.options);
  }
};
</script>
