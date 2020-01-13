<template>
  <v-expansion-panels>
    <v-expansion-panel>
      <v-expansion-panel-header>BASELINE</v-expansion-panel-header>
      <v-expansion-panel-content>
        <baseline-run-filter />
        <baseline-tag-filter />
      </v-expansion-panel-content>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script>
import {
  VExpansionPanels,
  VExpansionPanel,
  VExpansionPanelHeader,
  VExpansionPanelContent
} from "Vuetify/VExpansionPanel";

import BaselineRunFilter from './BaselineRunFilter';
import BaselineTagFilter from './BaselineTagFilter';

export default {
  name: 'BaselineFilter',
  components: {
    VExpansionPanels, VExpansionPanel, VExpansionPanelHeader,
    VExpansionPanelContent,
    BaselineRunFilter,
    BaselineTagFilter
  }
}
</script>
