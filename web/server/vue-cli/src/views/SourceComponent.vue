<template>
  <v-container fluid>
    <h1>Manage source components</h1>
    <span
      class="subtitle-1"
    >
      Group different source files and filter them as one.
    </span>
    <list-source-components />
  </v-container>
</template>

<script setup>
import { ListSourceComponents } from "@/components/Report/SourceComponent";
</script>
