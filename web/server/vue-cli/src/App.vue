<template>
  <div id="app">
    <router-link :to="{ name: 'products' }">
      Products
    </router-link>
    <router-link :to="{ name: 'login' }">
      Login
    </router-link>
    <router-link :to="{ name: 'global-permission' }">
      Global permissions
    </router-link>
    <router-link :to="{ name: 'product-new' }">
      New product
    </router-link>
    <router-link :to="{ name: 'product-edit', params: { endpoint: 'Default' } }">
      Edit product
    </router-link>
    <router-link :to="{ name: 'product-permission', params: { endpoint: 'Default' } }">
      Product permissions
    </router-link>
    <router-link :to="{ name: 'runs', params: { endpoint: 'Default' } }">
      Product detail
    </router-link>
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style lang="scss">
#app {
  text-align: center;
  color: $cc-primary;
  margin-top: 60px;
}
</style>
