<template>
  <v-container>
    <h1>Manage source components</h1>
    <list-source-components />
  </v-container>
</template>

<script>
import { ListSourceComponents } from "@/components/Report/SourceComponent";

export default {
  name: "SourceComponent",
  components: { ListSourceComponents }
};
</script>
