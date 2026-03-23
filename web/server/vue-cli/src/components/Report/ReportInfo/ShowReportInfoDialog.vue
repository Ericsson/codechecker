<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="1000px"
    title="Report Info"
    :buttons="false"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        id="report-info-btn"
        color="primary"
        variant="outlined"
        size="small"
        prepend-icon="mdi-help-circle-outline"
      >
        Report Info
      </v-btn>
    </template>
    <template v-slot:content>
      <report-info :value="value" />
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";
import ReportInfo from "./ReportInfo";

defineProps({
  value: { type: Object, default: null }
});

const dialog = ref(false);
</script>
