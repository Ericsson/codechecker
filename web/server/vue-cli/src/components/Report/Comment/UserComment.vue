<template>
  <v-timeline-item
    class="user-comment"
    dot-color="green"
    icon="mdi-account"
    size="small"
    fill-dot
  >
    <v-card
      class="elevation-2 d-flex"
    >
      <div class="flex-grow-1">
        <v-list
          lines="two"
        >
          <v-list-item>
            <template v-slot:prepend>
              <user-icon
                :value="comment.author"
                :size="32"
                class="mr-2"
                rounded="0"
              />
            </template>

            <v-list-item-title>
              {{ comment.author }}
            </v-list-item-title>

            <v-list-item-subtitle
              :title="comment.createdAt"
            >
              {{ createdAt }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <v-card-text class="pt-0 preserve-whitespace">
          {{ comment.message }}
        </v-card-text>
      </div>
      <div class="d-flex flex-column ga-1 pa-2">
        <v-btn
          class="edit-btn"
          icon="mdi-pencil"
          size="small"
          variant="text"
          @click="emit('update:comment', comment)"
        />
        <v-divider />
        <v-btn
          class="remove-btn"
          icon="mdi-trash-can-outline"
          size="small"
          variant="text"
          @click="emit('remove:comment', comment)"
        />
      </div>
    </v-card>
  </v-timeline-item>
</template>

<script setup>
import { formatDistanceToNow, parse } from "date-fns";
import { computed } from "vue";

import { UserIcon } from "@/components/Icons";

const props = defineProps({
  comment: { type: Object, required: true }
});

const emit = defineEmits([ "update:comment", "remove:comment" ]);

const createdAt = computed(() => {
  const created = parse(props.comment.createdAt,
    "yyyy-MM-dd HH:mm:ss.SSSSSS", new Date());
  return formatDistanceToNow(created);
});
</script>

<style scoped>
.preserve-whitespace {
  white-space: pre-wrap;
}
</style>