<template>
  <ConfirmDialog
    v-model="dialog"
    confirm-btn-label="Change"
    title="Change announcement"
    @confirm="confirmAnnouncementChange"
    @cancel="resetValue"
  >
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        id="edit-announcement-btn"
        color="primary"
        class="mr-2"
        variant="outlined"
      >
        <template v-slot:prepend>
          <v-icon>mdi-bullhorn-outline</v-icon>
        </template>
        Edit announcement
      </v-btn>
    </template>

    <template v-slot:content>
      <v-text-field
        v-model="value"
        append-icon="mdi-bullhorn-outline"
        label="Announcement text"
        hide-details
        variant="outlined"
        clearable
        density="compact"
      />
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useStore } from "vuex";

import { confService, handleThriftError } from "@cc-api";

import { GET_ANNOUNCEMENT } from "@/store/actions.type";
import { SET_ANNOUNCEMENT } from "@/store/mutations.type";

import ConfirmDialog from "@/components/ConfirmDialog";

const store = useStore();
const dialog = ref(false);
const value = ref(null);
const originalValue = ref(null);

const announcement = computed(() => store.getters.announcement);

onMounted(() => {
  if (announcement.value) {
    value.value = announcement.value;
    originalValue.value = announcement.value;
  } else {
    store.dispatch(GET_ANNOUNCEMENT).then(result => {
      value.value = result;
      originalValue.value = result;
    });
  }
});

function confirmAnnouncementChange() {
  const announcementB64 = value.value
    ? window.btoa(value.value) : window.btoa("");

  confService.getClient().setNotificationBannerText(announcementB64,
    handleThriftError(() => {
      dialog.value = false;
      store.commit(SET_ANNOUNCEMENT, value.value);
    }));
}

function resetValue() {
  dialog.value = false;
  value.value = originalValue.value;
}
</script>
