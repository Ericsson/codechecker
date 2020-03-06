<template>
  <confirm-dialog
    v-model="dialog"
    confirm-btn-label="Change"
    @confirm="confirmAnnouncementChange"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        class="mr-2"
        v-on="on"
      >
        <v-icon left>
          mdi-bullhorn-outline
        </v-icon>
        Edit announcement
      </v-btn>
    </template>

    <template v-slot:title>
      Change announcement
    </template>

    <template v-slot:content>
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
    </template>
  </confirm-dialog>
</template>

<script>
import { confService } from "@cc-api";

import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  name: "EditAnnouncementBtn",
  components: {
    ConfirmDialog
  },

  data() {
    return {
      dialog: false,
      announcement: ""
    };
  },
  mounted() {
    confService.getClient().getNotificationBannerText((err, announcement) => {
      this.announcement = window.atob(announcement);
    });
  },
  methods: {
    confirmAnnouncementChange() {
      const announcementB64 = this.announcement
        ? window.btoa(this.announcement) : window.btoa("");

      confService.getClient().setNotificationBannerText(announcementB64,
        () => {
          this.dialog = false;
        });
    }
  }
};
</script>
