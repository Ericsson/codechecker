<template>
  <v-radio-group class="px-7" :value="value" @change="emitUpdate">
    <template v-slot:label>
      <div>Report filter mode</div>
    </template>
    <v-radio value="end">
      <template v-slot:label>
        <span>
          End of report path
          <tooltip-help-icon>
            Filters reports with final error location within the
            selected component(s).
          </tooltip-help-icon>
        </span>
      </template>
    </v-radio>
    <v-radio value="anywhere">
      <template v-slot:label>
        <span>
          Anywhere on report path
          <tooltip-help-icon>
            Filters reports that have any bug path element within the
            selected component(s).
          </tooltip-help-icon>
        </span>
      </template>
    </v-radio>
    <v-radio value="single-origin">
      <template v-slot:label>
        <span>
          Single origin
          <tooltip-help-icon>
            Filters reports with the full bug path contained within the
            selected component(s).
          </tooltip-help-icon>
        </span>
      </template>
    </v-radio>
  </v-radio-group>
</template>

<script>
import TooltipHelpIcon from "@/components/TooltipHelpIcon.vue";

export default {
  name: "ReportFilterModeSelector",
  components: { TooltipHelpIcon },
  props: {
    value: {
      type: String,
      default: ""
    }
  },
  methods: {
    emitUpdate(selection) {
      this.$emit("input", selection);
    }
  }
};
</script>