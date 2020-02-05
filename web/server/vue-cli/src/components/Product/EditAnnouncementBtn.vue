<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="600px"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        class="mr-2"
        v-on="on"
      >
        Edit announcement
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Change announcement

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-container>
          <v-text-field
            v-model="announcement"
            append-icon="mdi-bullhorn-outline"
            label="Write your alert here..."
            single-line
            hide-details
            outlined
            solo
            clearable
            flat
            dense
          />
        </v-container>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          text
          @click="confirmAnnouncementChange"
        >
          Change
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { confService } from "@cc-api";

export default {
  name: "EditAnnouncementBtn",
  data() {
    return {
      dialog: false,
      announcement: ""
    };
  },
  mounted() {
    confService.getClient().getNotificationBannerText((err, announcement) => {
      this.announcement = window.atob(announcement);
    })
  },
  methods: {
    confirmAnnouncementChange() {
      const announcementB64 = this.announcement
        ? window.btoa(this.announcement) : window.btoa("");

      confService.getClient().setNotificationBannerText(announcementB64,
      () => {
        this.dialog = false;
      })
    }
  }
}
</script>
