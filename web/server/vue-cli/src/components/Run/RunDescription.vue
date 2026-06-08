<template>
  <v-menu
    content-class="run-description-menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-x
  >
    <template v-slot:activator="{ on }">
      <v-icon color="primary" class="description" v-on="on">
        mdi-information-outline
      </v-icon>
    </template>
    <v-card>
      <v-card-title>Description</v-card-title>
      <v-card-text>{{ value }}</v-card-text>
    </v-card>
  </v-menu>
</template>

<script>
export default {
  name: "RunDescription",
  props: {
    value: { type: String, required: true }
  }
};
</script>
