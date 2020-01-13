<template>
  <v-checkbox
    v-model="reportFilter.isUnique"
    :label="'Unique reports'"
  />
</template>

<script>
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";

export default {
  name: 'UniqueFilter',
  components: {
    VCheckbox
  },
  props: {
    reportFilter: { type: Object, required: true }
  }
}
</script>
