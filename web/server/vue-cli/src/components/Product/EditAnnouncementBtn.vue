<template>
  <ConfirmDialog
    v-model="dialog"
    confirm-btn-label="Change"
    title="Change announcement"
    icon="mdi-bullhorn-outline"
    @confirm="confirmAnnouncementChange"
    @cancel="resetValue"
  >
    <template v-slot:activator="{ props }">
      <v-btn
        id="edit-announcement-btn"
        class="mr-2"
        v-bind="props"
        height="40"
        color="primary"
        variant="tonal"
      >
        <template v-slot:prepend>
          <v-icon>mdi-bullhorn-outline</v-icon>
        </template>
        Edit announcement
      </v-btn>
    </template>

    <template v-slot:content>
      <div class="text-body-large text-medium-emphasis mb-2">
        Announcement Text
      </div>
      <v-text-field
        v-model="value"
        hide-details
        variant="outlined"
        clearable
        density="compact"
        placeholder="Accouncement Text"
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
