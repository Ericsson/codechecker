<template>
  <NotificationToast
    v-for="(notification, idx) in notifications"
    :key="notification.id"
    :notification="notification"
    :index="idx"
    @remove="removeNotification"
  />
</template>

<script setup>
import { REMOVE_NOTIFICATION } from "@/store/mutations.type";
import { computed } from "vue";
import { useStore } from "vuex";

import NotificationToast from "@/components/NotificationToast";

const store = useStore();

const notifications = computed(() => store.getters.notifications);

const removeNotification = id => store.commit(REMOVE_NOTIFICATION, id);
</script>
