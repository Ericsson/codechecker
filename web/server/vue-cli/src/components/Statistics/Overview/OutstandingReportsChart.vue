<script>
import _ from "lodash";
import {
  endOfMonth, endOfWeek, endOfYear, format, subDays, subMonths, subWeeks,
  subYears
} from "date-fns";
import { Line, mixins } from "vue-chartjs";
import ChartDataLabels from "chartjs-plugin-datalabels";

import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, ReviewStatus, Severity } from "@cc/report-server-types";
import { DateMixin, SeverityMixin } from "@/mixins";

const { reactiveData } = mixins;

export default {
  name: "OutstandingReportsChart",
  extends: Line,
  mixins: [ DateMixin, reactiveData, SeverityMixin ],
  props: {
    bus: { type: Object, required: true },
    getStatisticsFilters: { type: Function, required: true },
    interval: { type: String, required: true },
    resolution: { type: String, required: true },
  },
  data() {
    return {
      dates: [],
      options: {
        legend: {
          display: true,
        },
        responsive: true,
        maintainAspectRatio: false,
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
        scales: {
          xAxes: [
            {
              ticks: {
                padding: 10
              }
            }
          ]
        }
      },
      chartData: {
        labels: [],
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
              data: []
            };
          })
        ]
      }
    };
  },

  watch: {
    interval: {
      handler: _.debounce(function () {
        const oldSize = this.dates.length;
        const newSize = parseInt(this.interval);

        this.setChartData();

        if (newSize > oldSize) {
          const dates = this.dates.slice(oldSize);
          this.fetchData(dates);
        }
      }, 500)
    },
    resolution() {
      this.setChartData();
      this.fetchData(this.dates);
    }
  },

  created() {
    this.setChartData();
  },

  mounted() {
    this.addPlugin(ChartDataLabels);

    // Initialize the chart.
    this.renderChart(this.chartData, this.options);
  },

  activated() {
    this.bus.$on("refresh", () => this.fetchData(this.dates));
  },

  methods: {
    setChartData() {
      const interval = parseInt(this.interval);
      if (isNaN(interval) || interval <=0)
        return;

      let dateFormat = "yyyy. MMM. dd";

      if (this.resolution === "days") {
        const today = new Date();
        this.dates = [ ...new Array(interval).keys() ].map(i =>
          subDays(today, i));
      }
      else if (this.resolution === "weeks") {
        const endOfCurrentWeek = endOfWeek(new Date(), { weekStartsOn: 1 });
        this.dates = [ ...new Array(interval).keys() ].map(i =>
          subWeeks(endOfCurrentWeek, i));
      }
      else if (this.resolution === "months") {
        const endOfCurrentMonth = endOfMonth(new Date());
        this.dates = [ ...new Array(interval).keys() ].map(i =>
          subMonths(endOfCurrentMonth, i));

        dateFormat = "yyyy. MMM";
      }
      else if (this.resolution === "years") {
        const endOfCurrentYear = endOfYear(new Date());
        this.dates = [ ...new Array(interval).keys() ].map(i =>
          subYears(endOfCurrentYear, i));

        dateFormat = "yyyy";
      }

      this.chartData.labels = [ ...this.dates ].reverse().map((d, idx) => {
        const date = format(d, dateFormat);
        if (idx === this.dates.length - 1)
          return `${date} (Current)`;
        return date;
      });

      this.chartData.datasets.forEach(d => {
        if (this.dates.length > d.data.length) {
          d.data = [
            ...new Array(this.dates.length - d.data.length).fill(null),
            ...d.data
          ];
        } else {
          d.data = d.data.slice(d.data.length - this.dates.length,
            d.data.length);
        }
      });

      this.chartData = { ...this.chartData };
    },
    fetchData(datesToUpdate) {
      this.dates.forEach(async (d, idx) => {
        if (!datesToUpdate.includes(d)) return;

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

      const rFilter = new ReportFilter(reportFilter);
      rFilter.openReportsDate = this.getUnixTime(date);
      rFilter.detectionStatus = null;
      rFilter.reviewStatus =
        [ ReviewStatus.UNREVIEWED, ReviewStatus.CONFIRMED ];

      const cmpData = null;

      return new Promise(resolve => {
        ccService.getClient().getSeverityCounts(runIds, rFilter, cmpData,
          handleThriftError(res => resolve(res)));
      });
    }
  }
};
</script>
