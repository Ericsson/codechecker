<template>
  <v-dialog
    v-model="dialog"
    width="500"
    :scrollable="true"
  >
    <v-card>
      <v-card-title
        class="headline primary black-text"
        primary-title
      >
        Credits

        <v-spacer />

        <v-btn icon @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-list>
          <v-list-item
            v-for="credit in credits"
            :key="credit.name"
          >
            <template v-slot:prepend>
              <v-btn
                :href="`http://github.com/${credit.github}`"
                target="_blank"
                icon
                color="primary"
              >
                <v-icon>mdi-github</v-icon>
              </v-btn>
            </template>

            <v-list-item-title>{{ credit.name }}</v-list-item-title>
            <v-list-item-subtitle>{{ credit.email }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-card>
    <v-list>
      <v-list-item
        href="http://github.com/Ericsson/codechecker"
        target="_blank"
      >
        <template v-slot:prepend>
          <v-icon>mdi-github</v-icon>
        </template>
        <v-list-item-title>
          CodeChecker @ GitHub
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        href="http://github.com/Ericsson/codechecker/issues/new"
        target="_blank"
      >
        <template v-slot:prepend>
          <v-icon>mdi-bug</v-icon>
        </template>
        <v-list-item-title>
          Send bug report
        </v-list-item-title>
      </v-list-item>

      <CreditsDialog />

      <v-list-item
        :to="{ name: 'userguide' }"
      >
        <template v-slot:prepend>
          <v-icon>mdi-information-outline</v-icon>
        </template>
        <v-list-item-title>
          User guide
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        :to="{ name: 'new-features' }"
      >
        <template v-slot:prepend>
          <v-icon>mdi-star-circle-outline</v-icon>
        </template>
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
