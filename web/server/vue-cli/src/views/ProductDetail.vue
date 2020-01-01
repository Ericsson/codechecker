<template>
  <div id="product">
    <h3>Product Detail</h3>
    <router-link :to="{ name: 'runs' }">
      Runs
    </router-link>
    <router-link :to="{ name: 'statistics' }">
      Statistics
    </router-link>
    <router-link :to="{ name: 'reports' }">
      Reports
    </router-link>
    <router-link :to="{ name: 'report-detail', params: { name: 'run_name' }}">
      Report detail
    </router-link>
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'Product'
}
</script>
