<template>
  <v-select
    v-model="active"
    :items="items"
    :hide-details="true"
    class="select-same-report small"
    label="Found in"
    item-title="label"
    item-value="id"
    height="0"
    flat
    density="compact"
    variant="solo"
    @update:model-value="selectSameReport"
  >
    <template v-slot:selection="{ item }">
      <div class="d-flex align-center">
        <detection-status-icon
          class="mr-2"
          :status="item.raw.detectionStatus"
          :size="16"
        />
        <review-status-icon
          class="mr-2"
          :status="item.raw.reviewStatus"
          :size="16"
        />
        <span
          class="mr-2"
        >
          {{ item.raw.runName }}:{{ item.raw.fileName }}:L{{ item.raw.line }}
        </span>
        <v-chip
          class="text-black"
          :color="bugPathLenColor.getBugPathLenColor(item.raw.bugPathLength)"
          label
          size="small"
          variant="flat"
        >
          {{ item.raw.bugPathLength }}
        </v-chip>
      </div>
    </template>

    <template v-slot:item="{ item, props: listItemProps }">
      <v-list-item
        v-bind="listItemProps"
        :title="null"
        density="compact"
      >
        <detection-status-icon
          class="mr-2"
          :status="item.raw.detectionStatus"
          :size="16"
        />
        <review-status-icon
          class="mr-2"
          :status="item.raw.reviewStatus"
          :size="16"
        />
        <span
          class="mr-2"
        >
          {{ item.raw.runName }}:{{ item.raw.fileName }}:L{{ item.raw.line }}
        </span>
        <v-chip
          class="text-black"
          :color="bugPathLenColor.getBugPathLenColor(item.raw.bugPathLength)"
          label
          size="small"
          variant="flat"
        >
          {{ item.raw.bugPathLength }}
        </v-chip>
      </v-list-item>
    </template>
  </v-select>
</template>

<script setup>
import { ccService } from "@cc-api";
import { onMounted, ref, watch } from "vue";

import { DetectionStatusIcon, ReviewStatusIcon } from "@/components/Icons";
import { useBugPathLenColor } from "@/composables/useBugPathLenColor";

const props = defineProps({
  report: { type: Object, default: null }
});

const emit = defineEmits([ "update:report" ]);

const items = ref([]);
const active = ref(null);
const bugPathLenColor = useBugPathLenColor();

watch(() => props.report, () => {
  init();
});

onMounted(() => {
  init();
});

function init() {
  if (!props.report) return;

  active.value = props.report.reportId;
  getSameReports();
}

function getSameReports() {
  ccService.getSameReports(props.report.bugHash).then(_reports => {
    items.value = _reports.map(_report => {
      const fileName = _report.checkedFile.replace(/^.*[\\/]/, "");
      return {
        id: _report.reportId,
        label: `${_report.$runName}:${fileName}:L${_report.line}`,
        runName: _report.$runName,
        fileName: _report.checkedFile.replace(/^.*[\\/]/, ""),
        line: _report.line,
        bugPathLength: _report.bugPathLength,
        detectionStatus: _report.detectionStatus,
        reviewStatus: _report.reviewData.status
      };
    });
  });
}

function selectSameReport(reportId) {
  emit("update:report", reportId.toNumber());
}
</script>

<style lang="scss">
:deep(.v-select__selections input) {
  display: none;
}

.v-select.v-text-field--outlined {
  :deep(.theme--light.v-label) {
    background-color: #fff;
  }
}
</style>
