<template>
  <v-checkbox
    v-model="reportFilter.isUnique"
  >
    <template v-slot:label>
      Unique reports
      <v-tooltip max-width="200" right>
        <template v-slot:activator="{ on }">
          <v-icon
            color="accent"
            class="ml-1"
            v-on="on"
          >
            mdi-help-circle
          </v-icon>
        </template>
        <span>
          This narrows the report list to unique bug. The same bug may appear
          several times if it is found on different control paths, i.e. through
          different function calls. By checking <b>Unique reports</b> a report
          appears only once even if it is found on several paths.
        </span>
      </v-tooltip>
    </template>
  </v-checkbox>
</template>

<script>
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";
import VTooltip from "Vuetify/VTooltip/VTooltip";
import VIcon from "Vuetify/VIcon/VIcon";

export default {
  name: 'UniqueFilter',
  components: {
    VCheckbox, VTooltip, VIcon
  },
  props: {
    reportFilter: { type: Object, required: true }
  }
}
</script>
