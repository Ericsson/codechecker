<template>
  <v-row>
    <v-col
      v-for="(checker, idx) in checkers"
      :key="idx"
      cols="6"
    >
      <Checker
        :name="checker[0]"
        :enabled="checker[1].enabled"
      />
    </v-col>
  </v-row>
</template>

<script setup>
import Checker from "./Checker";

defineProps({
  checkers: { type: Array, required: true }
});
</script>
