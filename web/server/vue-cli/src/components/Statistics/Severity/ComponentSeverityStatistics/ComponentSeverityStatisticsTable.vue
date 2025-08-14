<script>
import { ComponentStatisticsTable } from "@/components/Statistics";

export default {
  name: "ComponentSeverityStatisticsTable",
  extends: ComponentStatisticsTable,
  data() {
    return {
      headers: [
        {
          text: "",
          value: "data-table-expand"
        },
        {
          text: "Component",
          value: "component",
          align: "center"
        },
        {
          text: "Critical",
          value: "critical.count",
          align: "center"
        },
        {
          text: "High",
          value: "high.count",
          align: "center"
        },
        {
          text: "Medium",
          value: "medium.count",
          align: "center"
        },
        {
          text: "Low",
          value: "low.count",
          align: "center"
        },
        {
          text: "Style",
          value: "style.count",
          align: "center"
        },
        {
          text: "Unspecified",
          value: "unspecified.count",
          align: "center"
        },
        {
          text: "All reports",
          value: "reports.count",
          align: "center"
        }
      ]
    };
  }
};
</script>

<style lang="scss" scoped>
// This section is needed to override the default inherited style.
</style>
