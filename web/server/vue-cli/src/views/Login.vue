<template>
  <div>
    <h3>Login</h3>
    <form @submit.prevent="onSubmit(username, password)">
      <input
        v-model="username"
        type="text"
        placeholder="User name"
      >
      <input
        v-model="password"
        type="password"
        placeholder="Password"
      >
      <button>Login</button>
    </form>
    <button @click="logout()">
      Logout
    </button>
  </div>
</template>

<script>
import { mapState } from "vuex";
import { LOGIN, LOGOUT } from "@/store/actions.type";

export default {
  name: "Login",
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
    onSubmit(username, password) {
      this.$store
        .dispatch(LOGIN, { username, password })
        .then(() => this.$router.push({ name: "products" }));
    },
    logout() {
      this.$store
        .dispatch(LOGOUT);
    }
  }
};
</script>
