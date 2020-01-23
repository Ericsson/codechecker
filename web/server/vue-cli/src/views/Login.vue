<template>
  <v-row align="center" justify="center">
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary" dark flat>
          <v-toolbar-title>Login</v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="username"
              label="Username"
              name="username"
              prepend-icon="mdi-account"
              type="text"
            />

            <v-text-field
              id="password"
              v-model="password"
              label="Password"
              name="password"
              prepend-icon="mdi-lock"
              type="password"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="login">
            Login
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>

<script>
import { VCard, VCardActions, VCardText } from "Vuetify/VCard";
import { VToolbar, VToolbarTitle } from "Vuetify/VToolbar";
import VTextField from "Vuetify/VTextField/VTextField";
import VSpacer from "Vuetify/VGrid/VSpacer";
import VForm from "Vuetify/VForm/VForm";
import VBtn from "Vuetify/VBtn/VBtn";

import VRow from "Vuetify/VGrid/VRow";
import VCol from "Vuetify/VGrid/VCol";

import { mapState } from "vuex";
import { LOGIN } from "@/store/actions.type";

export default {
  name: "Login",
  components: {
    VCard, VCardActions, VCardText, VToolbar, VToolbarTitle, VForm,
    VTextField, VSpacer, VBtn, VRow, VCol
  },

  data() {
    return {
      username: null,
      password: null
    };
  },

  computed: {
    ...mapState({
      errors: state => state.auth.errors
    })
  },

  methods: {
    login(username, password) {
      this.$store
        .dispatch(LOGIN, { username, password })
        .then(() => this.$router.push({ name: "products" }));
    }
  }
};
</script>