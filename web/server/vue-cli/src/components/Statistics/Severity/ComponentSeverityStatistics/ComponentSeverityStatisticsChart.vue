<script>
import { Pie, mixins } from "vue-chartjs";
import ChartDataLabels from "chartjs-plugin-datalabels";
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
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          datalabels: {
            backgroundColor: colors
          }
        }
      },
      chartData: {
        labels: labels,
        datasets: [
          {
            data: [],
            backgroundColor: colors,
            datalabels: {
              color: "white",
              borderColor: "white",
              borderRadius: 25,
              borderWidth: 2,
              font: {
                weight: "bold"
              },
            }
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
    this.addPlugin(ChartDataLabels);

    this.renderChart(this.chartData, this.options);
  }
};
</script>
