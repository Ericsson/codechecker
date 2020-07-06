<template>
  <confirm-dialog
    v-model="dialog"
    confirm-btn-label="Change"
    @confirm="confirmAnnouncementChange"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        id="edit-announcement-btn"
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
        v-model="value"
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
import { mapActions, mapGetters, mapMutations } from "vuex";

import { confService, handleThriftError } from "@cc-api";

import { GET_ANNOUNCEMENT } from "@/store/actions.type";
import { SET_ANNOUNCEMENT } from "@/store/mutations.type";

import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  name: "EditAnnouncementBtn",
  components: {
    ConfirmDialog
  },

  data() {
    return {
      dialog: false,
      value: null
    };
  },

  computed: {
    ...mapGetters([
      "announcement"
    ])
  },

  mounted() {
    this.getAnnouncement().then(announcement => {
      this.value = announcement;
    });
  },

  methods: {
    ...mapActions([
      GET_ANNOUNCEMENT
    ]),
    ...mapMutations([
      SET_ANNOUNCEMENT
    ]),

    // TODO: set announcement back to the original value on cancel.
    confirmAnnouncementChange() {
      const announcementB64 = this.value
        ? window.btoa(this.value) : window.btoa("");

      confService.getClient().setNotificationBannerText(announcementB64,
        handleThriftError(() => {
          this.dialog = false;
          this.setAnnouncement(this.value);
        }));
    }
  }
};
</script>
