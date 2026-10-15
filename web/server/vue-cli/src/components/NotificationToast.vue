<template>
  <v-snackbar
    v-model="visible"
    :color="color"
    location="top right"
    :timeout="-1"
    :style="offsetStyle"
    class="notification-toast"
    transition="slide-x-reverse-transition"
    @after-leave="emit('remove', notification.id)"
  >
    <div class="d-flex align-start">
      <v-icon class="mr-2 mt-1">
        {{ icon }}
      </v-icon>
      <div>
        <div
          v-if="notification.title"
          class="notification-toast__title"
        >
          {{ notification.title }}
        </div>
        <div class="notification-toast__message">
          {{ notification.message }}
        </div>
      </div>
    </div>

    <template v-slot:actions>
      <v-btn
        icon="mdi-close"
        size="small"
        variant="text"
        @click="close"
      />
    </template>

    <v-progress-linear
      class="notification-toast__progress"
      :model-value="progress"
      color="white"
      height="3"
    />
  </v-snackbar>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  notification: { type: Object, required: true },
  // Stacking index, used to offset each toast vertically.
  index: { type: Number, default: 0 },
  defaultTimeout: { type: Number, default: 5000 }
});

const emit = defineEmits([ "remove" ]);

const visible = ref(true);
const progress = ref(100);

const timeout = computed(
  () => props.notification.timeout ?? props.defaultTimeout);

// Derive the snackbar color and leading icon from the notification type.
const color = computed(() =>
  props.notification.type === "success" ? "success" : "error");

const icon = computed(() =>
  props.notification.type === "success"
    ? "mdi-check-circle-outline"
    : "mdi-alert-outline");

// Offset stacked toasts so they do not overlap.
const offsetStyle = computed(() => ({
  "margin-top": `${props.index * 72}px`
}));

let intervalId = null;
const tickMs = 50;

// Trigger the exit: setting `visible` to false lets the v-snackbar play its
// slide-out transition. The `@after-leave` hook then emits `remove` once the
// animation has finished, so the toast fades out instead of vanishing.
function close() {
  if (intervalId !== null) {
    clearInterval(intervalId);
    intervalId = null;
  }
  visible.value = false;
}

onMounted(() => {
  // A non-positive timeout means the notification should persist until the
  // user dismisses it manually. Keep the progress bar full and skip the timer.
  if (timeout.value <= 0) {
    progress.value = 100;
    return;
  }

  const start = Date.now();

  intervalId = setInterval(() => {
    const elapsed = Date.now() - start;
    progress.value = Math.max(0, 100 - (elapsed / timeout.value) * 100);

    if (elapsed >= timeout.value) {
      close();
    }
  }, tickMs);
});

onBeforeUnmount(() => {
  if (intervalId !== null) clearInterval(intervalId);
});
</script>

<style scoped>
.notification-toast__title {
  font-weight: 600;
  margin-bottom: 2px;
}

.notification-toast__message {
  white-space: pre-line;
  word-break: break-word;
}

.notification-toast__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
}
</style>
