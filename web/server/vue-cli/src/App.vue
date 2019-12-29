<template>
  <div id="app">
    <Simple msg="CodeChecker Vue CLI"/>
  </div>
</template>

<script>
import Simple from './components/Simple.vue'

export default {
  name: 'app',
  components: {
    Simple
  }
}
</script>

<style>
#app {
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
