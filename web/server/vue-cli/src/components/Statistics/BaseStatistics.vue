<script setup>
import { useBaseStatistics } from "@/composables/useBaseStatistics";
import { onMounted } from "vue";

const props = defineProps({
  bus: { type: Object, required: true },
  namespace: { type: String, required: true }
});

const baseStats = useBaseStatistics(props, getStatistics);

baseStats.setupRefreshListener(fetchStatistics);

onMounted(function() {
  if (process.env.NODE_ENV !== "production") {
    if (module.hot) {
      if (module.hot.data) {
        baseStats.statistics.value = module.hot.data.statistics;
      }

      module.hot.dispose(
        _data => _data["statistics"] = baseStats.statistics.value
      );
    }
  }
});

function fetchStatistics() {}

function getStatistics(/* runIds, reportFilter, cmpData */) {}

defineExpose({
  fetchStatistics,
  fetchDifference: baseStats.fetchDifference,
  getStatistics,
  getStatisticsFilters: baseStats.getStatisticsFilters,
  statistics: baseStats.statistics
});
</script>