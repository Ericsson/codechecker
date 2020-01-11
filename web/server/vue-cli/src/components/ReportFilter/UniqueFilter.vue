<template>
  <v-checkbox
    v-model="isUnique"
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
  data() {
    return {
      isUnique: false
    };
  }
}
</script>
