<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="500px"
    title="Credits"
    :buttons="false"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-list-item
        v-bind="activatorProps"
        id="edit-global-permissions-btn"
      >
        <template v-slot:prepend>
          <v-icon>
            mdi-account-group-outline
          </v-icon>
        </template>
        <v-list-item-title>Credits</v-list-item-title>
      </v-list-item>
    </template>
    <template v-slot:content>
      <v-list>
        <v-list-item
          v-for="credit in credits"
          :key="credit.name"
        >
          <template v-slot:prepend>
            <v-btn
              :href="`http://github.com/${credit.github}`"
              target="_blank"
              icon="mdi-github"
              color="primary"
              variant="plain"
            />
          </template>

          <v-list-item-title>{{ credit.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ credit.email }}</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";

const dialog = ref(false);

const credits = ref([
  {
    name: "Barnabás Domozi",
    github: "",
    email:"barnabas.domozi.ext@ericsson.com"
  },
  {
    name: "Bence Babati",
    github: "babati",
    email: "bence.babati@ericsson.com"
  },
  {
    name: "Boldizsár Tóth",
    github: "bobszi",
    email: "toth.boldizsar@gmail.com"
  },
  { 
    name: "Dániel Krupp",
    github: "dkrupp",
    email: "daniel.krupp@ericsson.com"
  },
  {
    name: "Gábor Alex Ispánovics",
    github: "igalex",
    email: "gabor.alex.ispanovics@ericsson.com"
  },
  {
    name: "Gábor Horváth",
    github: "Xazax-hun",
    email: "gabor.a.horvath@ericsson.com"
  },
  {
    name: "Gergely Gulyás",
    github: "gulyasgergely902",
    email: "gergely.gulyas.ext@ericsson.com"
  },
  {
    name: "György Orbán",
    github: "gyorb",
    email: "gyorgy.orban@ericsson.com"
  },
  {
    name: "Kristóf Umann",
    github: "",
    email:"kristof.umann@ericsson.com"
  },
  {
    name: "Márton Csordás",
    github: "csordasmarton",
    email: "marton.csordas@ericsson.com"
  },
  {
    name: "Nóra Zinaeddin",
    github: "",
    email:"nora.zinaeddin.ext@ericsson.com"
  },
  {
    name: "Richárd Szalay",
    github: "whisperity",
    email: "richard.szalay@ericsson.com"
  },
  {
    name: "Szabolcs Sipos",
    github: "labuwx",
    email: "labuwx@balfug.com"
  },
  {
    name: "Tibor Brunner",
    github: "bruntib",
    email: "tibor.brunner@ericsson.com"
  }
]);
</script>

<style lang="scss">
</style>
