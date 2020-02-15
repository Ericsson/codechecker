<template>
  <v-footer color="secondary" padless>
    <v-row
      justify="center"
      no-gutters
    >
      <v-col
        class="py-3 text-center white--text"
        cols="5"
      >
        © {{ new Date().getFullYear() }} —
        <v-avatar size="24px" tile>
          <img
            alt="Ericsson"
            src="@/assets/ericsson.png"
          >
        </v-avatar>
        Ericsson
      </v-col>
    </v-row>
  </v-footer>
</template>

<script>
export default {
  name: "TheHeader"
};
</script>
