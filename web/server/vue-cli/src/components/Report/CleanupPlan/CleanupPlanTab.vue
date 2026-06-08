<template>
  <v-container>
    <v-tabs v-model="tab">
      <v-tab
        v-for="item in ['Open', 'Closed']"
        :key="item"
        class="font-weight-bold subtitle-2 text-capitalize"
      >
        {{ item }}
      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab">
      <v-tab-item>
        <slot name="open" />
      </v-tab-item>

      <v-tab-item>
        <slot name="closed" />
      </v-tab-item>
    </v-tabs-items>
  </v-container>
</template>

<script>
export default {
  name: "CleanupPlanTab",
  props: {
    value: { type: Number, default: null }
  },
  computed: {
    tab: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("input", val);
      }
    }
  }
};
</script>
