<template>
  <v-btn
    class="show-analysis-info-btn"
    color="primary"
    outlined
    small
    @click="$emit('click')"
  >
    <v-icon
      class="mr-1"
      small
    >
      mdi-console
    </v-icon>
    Analysis info
  </v-btn>
</template>
