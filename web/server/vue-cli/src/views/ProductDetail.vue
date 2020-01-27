<template>
  <div id="product">
    <v-tabs>
      <v-tab
        v-for="tab in tabs"
        :key="tab.id"
        :to="{ name: tab.route }"
        exact
      >
        {{ tab.name }}
      </v-tab>
    </v-tabs>
    <router-view />
  </div>
</template>

<script>
import VTab from "Vuetify/VTabs/VTab";
import VTabs from "Vuetify/VTabs/VTabs";

export default {
  name: "Product",
  components: {
    VTab, VTabs
  },
  data() {
    return {
      tabs: [
        { id: 1, name: "Runs", route: "runs" },
        { id: 2, name: "Statistics", route: "statistics" },
        { id: 3, name: "Reports", route: "reports" }
      ]
    };
  }
}
</script>
