<template>
  <v-footer color="secondary" padless>
    <v-row justify="center" no-gutters>
      <v-col
        class="py-2 text-center white--text"
        cols="12"
      >
        {{ new Date().getFullYear() }} — <strong>Ericsson</strong>
      </v-col>
    </v-row>
  </v-footer>
</template>

<script>
export default {
  name: "TheHeader"
};
</script>
