<template>
  <v-tooltip
    right
    color="white"
  >
    <template v-slot:activator="{ props }">
      <slot :on="props" />
    </template>

    <v-card
      v-if="value"
      class="mx-auto"
      variant="outlined"
    >
      <v-list-item
        v-for="v in value.split('\n')"
        :key="v"
        :class="[
          v[0] === '+' ? 'include' : v[0] === '-' ? 'exclude': 'other'
        ]"
        density="compact"
      >
        {{ v }}
      </v-list-item>
    </v-card>
  </v-tooltip>
</template>

<script setup>
defineProps({
  value: { type: String, required: true }
});
</script>

<style lang="scss" scoped>
.v-tooltip__content {
  padding: 0px;

  .v-list-item {
    min-height: auto;
  }

  .theme--light.v-list-item {
    &.include {
      color: green !important;
    }

    &.exclude {
      color: red !important;
    }

    &.other {
      color: black !important;
    }
  }
}
</style>
