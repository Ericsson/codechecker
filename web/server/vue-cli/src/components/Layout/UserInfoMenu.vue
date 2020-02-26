<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
  >
    <template v-slot:activator="{ on }">
      <v-btn
        text
        class="text-none"
        v-on="on"
      >
        <user-icon
          v-if="currentUser"
          :value="currentUser"
          :size="24"
          class="mr-2"
          txt-class="font-weight-bold white--text"
        />
        {{ currentUser }}
      </v-btn>
    </template>

    <v-card>
      <v-list>
        <v-list-item>
          <v-list-item-avatar>
            <user-icon
              :value="currentUser"
            />
          </v-list-item-avatar>

          <v-list-item-content>
            <v-list-item-title class="headline">
              {{ currentUser }}
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-card flat>
        <v-card-text>
          Permissions:
          <v-chip
            v-for="permission in permissions"
            :key="permission"
            class="ma-2"
            color="success"
            outlined
          >
            {{ permission }}
          </v-chip>
        </v-card-text>
      </v-card>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="primary"
          text
          @click="logOut"
        >
          Log out
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script>
import { mapActions, mapGetters } from "vuex";

import { UserIcon } from "@/components/Icons";
import { GET_LOGGED_IN_USER, LOGOUT } from "@/store/actions.type";

export default {
  name: "UserInfoMenu",
  components: {
    UserIcon
  },
  data() {
    return {
      menu: false,
      // TODO: get these from server.
      permissions: [ "Admin", "Store", "Access" ]
    };
  },
  computed: {
    ...mapGetters([
      "currentUser"
    ])
  },

  created() {
    this.getLoggedInUser();
  },

  methods: {
    ...mapActions([
      GET_LOGGED_IN_USER
    ]),

    logOut() {
      this.$store
        .dispatch(LOGOUT)
        .then(
          () => {
            this.$router.push({ name: "login" });
            this.menu = false;
          });
    }
  }
};
</script>