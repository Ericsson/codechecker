<template>
  <v-btn
    class="remove-btn"
    icon="mdi-trash-can-outline"
    size="x-small"
    @click="removeComment"
  />
</template>

<script setup>
const props = defineProps({
  comment: { type: Object, required: true }
});

const emit = defineEmits([ "remove:comment" ]);

function removeComment() {
  emit("remove:comment", props.comment);
}
</script>
