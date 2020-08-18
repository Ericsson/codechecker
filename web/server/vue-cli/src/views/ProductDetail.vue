<template>
  <v-container id="product" fluid>
    <keep-alive>
      <router-view />
    </keep-alive>
  </v-container>
</template>

<script>
export default {
  name: "Product"
};
</script>
