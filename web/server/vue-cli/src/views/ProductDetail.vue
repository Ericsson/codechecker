<template>
  <div id="product">
    <v-tabs>
      <v-tab :to="{ name: 'runs' }">
        Runs
      </v-tab>
      <v-tab :to="{ name: 'statistics' }">
        Statistics
      </v-tab>
      <v-tab :to="{ name: 'reports' }">
        Reports
      </v-tab>
      <v-tab :to="{ name: 'report-detail', params: { name: 'run_name' }}">
        Report detail
      </v-tab>
    </v-tabs>
    <router-view />
  </div>
</template>

<script>
import VTab from "Vuetify/VTabs/VTab";
import VTabs from "Vuetify/VTabs/VTabs";

export default {
  name: 'Product',
  components: {
    VTab, VTabs
  }
}
</script>
