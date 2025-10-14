<template>
  <v-btn
    id="save-report-filter-btn"
    outlined
    text
    color="primary"
    @click="emitSaveCurrentFilter"
  >
    <v-icon left>
      <!-- mdi-delete -->
    </v-icon>
    load current configuration
  </v-btn>
</template>

<script>
// import { BaseFilterMixin } from "./Filters";
import BaseSelectOptionFilterMixin from
  "./Filters/BaseSelectOptionFilter.mixin";
// import { ccService, handleThriftError } from "@cc-api";
// import { ReportFilter } from "@cc/report-server-types";

export default {
  name: "SaveReportFilter",
  // mixins: [ BaseFilterMixin ],
  mixins: [ BaseSelectOptionFilterMixin ],

  methods: {
    // getFilterPreset(){
    //   const preset_id = 1;
    //   console.log(this.ReportFilter);
    //   new Promise(resolve => {
    //     ccService.getClient().getFilterPreset(preset_id,
    //       handleThriftError(Filter_Preset => {
    //         resolve(Filter_Preset);
    //       })
    //     );
    //   })
    //     .then(Filter_Preset => {
    //       this.setReportFilter(
    //         new ReportFilter(Filter_Preset.reportFilter));

    //       this.$emit("refresh");
    //     }).catch(err => {
    //       handleThriftError("FAILURE", err);
    //     });
    // },
    // updateReportFilter() {
    //   this.setReportFilter({
    //     analyzerNames: this.selectedItems.map(item => item.id)
    //   });
    // },

    emitSaveCurrentFilter(){
      // this.refreshFilterState();
      // this.getFilterPreset();


      this.$emit("save_preset");
      this.$emit("update:url");
    }
  }
};
</script>
