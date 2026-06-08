<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-text class="px-0 pb-0">
            <alerts
              :success="success"
              success-msg="Successfully logged in!"
              :error="error"
              :error-msg="errorMsg"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters } from "vuex";
import { LOGIN } from "@/store/actions.type";
import Alerts from "@/components/Alerts.vue";


export default {
  name: "OAuthLogin",
  components: {
    alerts: Alerts
  },

  data() {
    return {
      success: false,
      error: false,
      errorMsg: null,
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

  mounted() {
    this.detectCallback();
  },

  methods: {
    detectCallback() {
      const params = this.$route.query;
      const url = window.location.href;
      const provider = this.$route.params.provider;

      if (params.code != null && params.state != null) {

        this.$store
          .dispatch(LOGIN, {
            type: "oauth",
            provider: provider,
            url: url
          })
          .then(() => {
            this.success = true;
            this.error = false;

            const w = window.location;
            window.location.href = w.origin + w.pathname;
          }).catch(err => {
            this.errorMsg = `Failed to log in! ${err.message}`;
            this.error = true;
            this.$router.replace({ name: "login" });
          });
      }
    },
  }
};
</script>

<style lang="scss" scoped>
#btn-container > button {
  margin: 0 !important;
  margin-top: 10px !important;
}

#avatar {
  position: absolute;
  margin: 0 auto;
  left: 0;
  right: 0;
  top: -70px;
  width: 95px;
  height: 95px;
  border-radius: 50%;
  z-index: 9;
  padding: 15px;
  box-shadow: 0px 2px 2px rgba(0, 0, 0, 0.1);
}

#login-btn {
  font-size: 1.2em;
}
</style>