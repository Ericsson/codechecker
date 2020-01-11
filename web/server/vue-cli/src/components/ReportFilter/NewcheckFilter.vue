<template>
  <v-expansion-panels>
    <v-expansion-panel>
      <v-expansion-panel-header>NEWCHECK</v-expansion-panel-header>
      <v-expansion-panel-content>
        <newcheck-run-filter />
        <newcheck-tag-filter />
        <newcheck-diff-type-filter />
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

import NewcheckRunFilter from './NewcheckRunFilter';
import NewcheckTagFilter from './NewcheckTagFilter';
import NewcheckDiffTypeFilter from './NewcheckDiffTypeFilter';

export default {
  name: 'BaselineFilter',
  components: {
    VExpansionPanels, VExpansionPanel, VExpansionPanelHeader,
    VExpansionPanelContent,
    NewcheckRunFilter,
    NewcheckTagFilter,
    NewcheckDiffTypeFilter
  }
}
</script>
