<template>
  <div>
    <v-dialog
      v-model="dialog"
      width="500"
      :scrollable="true"
    >
      <v-card>
        <v-card-title
          class="headline primary white--text"
          primary-title
        >
          Credits

          <v-spacer />

          <v-btn icon dark @click="dialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item
              v-for="credit in credits"
              :key="credit.name"
            >
              <v-list-item-avatar>
                <v-btn
                  :href="`http://github.com/${credit.github}`"
                  target="_blank"
                  icon
                  color="primary"
                >
                  <v-icon>mdi-github</v-icon>
                </v-btn>
              </v-list-item-avatar>

              <v-list-item-content>
                <v-list-item-title>{{ credit.name }}</v-list-item-title>
                <v-list-item-subtitle>{{ credit.email }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-list>
      <v-list-item
        href="http://github.com/Ericsson/codechecker"
        target="_blank"
      >
        <v-list-item-avatar>
          <v-icon>mdi-github</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>
          CodeChecker @ GitHub
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        href="http://github.com/Ericsson/codechecker/issues/new"
        target="_blank"
      >
        <v-list-item-avatar>
          <v-icon>mdi-bug</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>
          Send bug report
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        @click="openDialog"
      >
        <v-list-item-avatar>
          <v-icon>mdi-account-group-outline</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>
          Credits
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        :to="{ name: 'userguide' }"
      >
        <v-list-item-avatar>
          <v-icon>mdi-information-outline</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>
          User guide
        </v-list-item-title>
      </v-list-item>

      <v-list-item
        :to="{ name: 'new-features' }"
      >
        <v-list-item-avatar>
          <v-icon>mdi-star-circle-outline</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>
          New features
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
export default {
  name: "HeaderMenuItems",
  data() {
    return {
      dialog: false,
      credits: [
        { name: "Dániel Krupp",
          github: "dkrupp",
          email: "daniel.krupp@ericsson.com"
        },
        {
          name: "György Orbán",
          github: "gyorb",
          email: "gyorgy.orban@ericsson.com"
        },
        {
          name: "Tibor Brunner",
          github: "bruntib",
          email: "tibor.brunner@ericsson.com"
        },
        {
          name: "Gábor Horváth",
          github: "Xazax-hun",
          email: "gabor.a.horvath@ericsson.com"
        },
        {
          name: "Richárd Szalay",
          github: "whisperity",
          email: "richard.szalay@ericsson.com"
        },
        {
          name: "Márton Csordás",
          github: "csordasmarton",
          email: "marton.csordas@ericsson.com"
        },
        {
          name: "Boldizsár Tóth",
          github: "bobszi",
          email: "toth.boldizsar@gmail.com"
        },
        {
          name: "Bence Babati",
          github: "babati",
          email: "bence.babati@ericsson.com"
        },
        {
          name: "Gábor Alex Ispánovics",
          github: "igalex",
          email: "gabor.alex.ispanovics@ericsson.com"
        },
        {
          name: "Szabolcs Sipos",
          github: "labuwx",
          email: "labuwx@balfug.com"
        }
      ]
    };
  },

  methods: {
    openDialog() {
      // We have to use setTimeout if we would like to open a dialog on a
      // menu button.
      // See: https://github.com/vuetifyjs/vuetify/issues/7021
      setTimeout(() => {
        this.dialog = true;
      });
    }
  }
};
</script>
