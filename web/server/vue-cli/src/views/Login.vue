<template>
  <v-row align="center" justify="center">
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary" dark flat>
          <v-toolbar-title>Login</v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <alerts
            :success="success"
            success-msg="Successfully logged in!"
            :error="error"
            :error-msg="errorMsg"
          />

          <v-form>
            <v-text-field
              v-model="username"
              label="Username"
              name="username"
              prepend-icon="mdi-account"
              type="text"
              @keyup.enter="login"
            />

            <v-text-field
              id="password"
              v-model="password"
              label="Password"
              name="password"
              prepend-icon="mdi-lock"
              type="password"
              @keyup.enter="login"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            @click="login"
          >
            Login
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>

<script>
import { mapGetters } from "vuex";
import { LOGIN } from "@/store/actions.type";

import Alerts from "@/components/Alerts";

export default {
  name: "Login",
  components: {
    Alerts
  },
  data() {
    return {
      username: null,
      password: null,
      success: false,
      error: false,
      errorMsg: null
    };
  },

  computed: {
    ...mapGetters([
      "isAuthenticated"
    ])
  },

  created() {
    if (this.isAuthenticated) {
      this.$router.replace({ name: "products" });
    }
  },

  methods: {
    login() {
      this.$store
        .dispatch(LOGIN, { username: this.username, password: this.password })
        .then(() => {
          this.success = true;
          this.error = false;

          this.$router.push({ name: "products" });
        }).catch((err) => {
          this.errorMsg = `Failed to log in! ${err.message}`;
          this.error = true;
        });
    }
  }
};
</script>
