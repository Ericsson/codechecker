<template>
  <v-btn
    class="edit-btn"
    icon="mdi-pencil"
    size="x-small"
    @click="editComment"
  />
</template>

<script setup>

const props = defineProps({
  comment: { type: Object, required: true }
});

const emit = defineEmits([ "update:comment" ]);

function editComment() {
  emit("update:comment", props.comment);
}
</script>
