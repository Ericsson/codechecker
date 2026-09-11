<template>
  <v-card>
    <v-list>
      <v-list-item
        href="http://github.com/Ericsson/codechecker"
        target="_blank"
        prepend-icon="mdi-github"
        prepend-gap="8"
      >
        <v-list-item-title>
          CodeChecker @ GitHub
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        href="http://github.com/Ericsson/codechecker/issues/new"
        target="_blank"
        prepend-icon="mdi-bug"
        prepend-gap="8"
      >
        <v-list-item-title>
          Send bug report
        </v-list-item-title>
      </v-list-item>

      <CreditsDialog />

      <v-list-item
        :to="{ name: 'userguide' }"
        prepend-icon="mdi-information-outline"
        prepend-gap="8"
      >
        <v-list-item-title>
          User guide
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        :to="{ name: 'new-features' }"
        prepend-icon="mdi-star-circle-outline"
        prepend-gap="8"
      >
        <v-list-item-title>
          New features
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-card>
</template>

<script setup>
import CreditsDialog from "@/components/CreditsDialog.vue";
</script>
