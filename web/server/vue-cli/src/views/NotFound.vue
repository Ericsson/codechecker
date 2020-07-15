<template>
  <v-container
    class="text-center"
    fill-height
  >
    <v-row align="center">
      <v-col>
        <h1 class="display-2 primary--text">
          Whoops, 404
        </h1>

        <p>The page you were looking for does not exist!</p>

        <v-btn
          :to="{ name: 'products' }"
          color="primary"
          outlined
        >
          <v-icon left>
            mdi-briefcase-outline
          </v-icon>
          Back to products
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: "NotFound"
};
</script>
