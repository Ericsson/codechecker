<template>
  <h3>{{ msg }}</h3>
</template>

<script>
export default {
  name: 'Simple',
  props: {
    msg: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
h3 {
  margin: 40px 0 0;
}
</style>
