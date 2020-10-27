<script>
import { endOfMonth, format, subMonths } from "date-fns";
import { Line, mixins } from "vue-chartjs";
import ChartDataLabels from "chartjs-plugin-datalabels";

import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, Severity } from "@cc/report-server-types";
import { DateMixin, SeverityMixin } from "@/mixins";

const { reactiveData } = mixins;

export default {
  name: "OutstandingReportsChart",
  extends: Line,
  mixins: [ DateMixin, reactiveData, SeverityMixin ],
  props: {
    bus: { type: Object, required: true },
    getStatisticsFilters: { type: Function, required: true }
  },
  data() {
    const startOfCurrentMonth = endOfMonth(new Date());

    const dates = [ ...new Array(12).keys() ].map(i =>
      subMonths(startOfCurrentMonth, i));

    return {
      dates,
      options: {
        legend: {
          display: true,
        },
        responsive: true,
        maintainAspectRatio: false,
        title: {
          display: true,
          text: "Number of outstanding reports"
        },
        tooltips: {
          mode: "index",
          callbacks: {
            footer: function (tooltipItems, data) {
              const total = tooltipItems.reduce((acc, curr) => {
                return acc + data.datasets[curr.datasetIndex].data[curr.index];
              }, 0);

              return `Total: ${total}`;
            },
          },
          intersect: false
        },
        hover: {
          mode: "nearest",
          intersect: true
        },
      },
      chartData: {
        labels: [ ...dates ].reverse().map((d, idx) => {
          const date = format(d, "yyyy MMM");
          if (idx === dates.length - 1)
            return `${date} (Current)`;
          return date;
        }),
        datasets: [
          ...Object.keys(Severity).reverse().map(s => {
            const severityId = Severity[s];
            const color = this.severityFromCodeToColor(severityId);

            return {
              type: "line",
              label: this.severityFromCodeToString(severityId),
              backgroundColor: color,
              borderColor: color,
              borderWidth: 3,
              fill: false,
              pointRadius: 5,
              pointHoverRadius: 10,
              datalabels: {
                backgroundColor: color,
                color: "white",
                borderRadius: 4,
                font: {
                  weight: "bold"
                },
              },
              data: dates.map(() => null)
            };
          })
        ]
      }
    };
  },
  mounted() {
    this.addPlugin(ChartDataLabels);

    // Initialize the chart.
    this.renderChart(this.chartData, this.options);
  },
  activated() {
    this.bus.$on("refresh", () => this.fetchData());
  },
  methods: {
    fetchData() {
      this.dates.forEach(async (d, idx) => {
        const reportCount = await this.fetchOutstandingReports(d);
        const datasets = this.chartData.datasets;

        Object.keys(Severity).reverse().forEach((s, i) => {
          const severityId = Severity[s];
          const numOfReports = reportCount[severityId]?.toNumber() || 0;

          const data = datasets[i].data;
          data[data.length - 1 - idx] = numOfReports;
        });

        this.chartData = { ...this.chartData };
      });
    },

    fetchOutstandingReports(date) {
      const { runIds, reportFilter } = this.getStatisticsFilters();
      const cmpData = null;

      const rFilter = new ReportFilter(reportFilter);
      rFilter.openReportsDate = this.getUnixTime(date);

      return new Promise(resolve => {
        ccService.getClient().getSeverityCounts(runIds, rFilter, cmpData,
          handleThriftError(res => resolve(res)));
      });
    }
  }
};
</script>
