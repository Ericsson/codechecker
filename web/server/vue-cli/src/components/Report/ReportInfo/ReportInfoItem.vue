<template>
  <div>
    <div
      class="
        text-caption
        text-uppercase
        font-weight-bold
        text-grey-darken-1
        mb-1
    "
    >
      {{ title }}
      <v-icon
        v-if="value && !iconShown && !chip"
        class="ml-1"
        size="small"
        @click="copyToClipboard"
      >
        {{ isCopied ? 'mdi-check' : 'mdi-content-copy' }}
      </v-icon>
      <v-chip
        v-if="value && docUrl"
        class="ml-2"
        size="x-small"
        color="primary"
        :ripple="false"
        append-icon="mdi-open-in-new"
        :href="props.docUrl"
        target="_blank"
      >
        Documentation
      </v-chip>
    </div>
    <div
      class="text-body-1 font-weight-medium"
    >
      <component
        :is="query != null ? 'router-link' : 'span'"
        v-bind="query != null ? { to: query } : {}"
        :class="query != null ? 'text-primary' : ''"
      >
        <v-chip
          v-if="chip"
          class="text-black"
          :color="gradientColor.getGradientColor(value)"
          size="small"
          variant="flat"
        >
          <span v-if="value">{{ value }}</span>
          <span v-else>-</span>
        </v-chip>
        <slot v-else-if="iconShown" name="icon" />
        <span v-else>
          {{ value }}
        </span>
      </component>
    </div>
  </div>
</template>
<script setup>
import { ref } from "vue";
import { useGradientColor } from "@/composables/useGradientColor";

const props = defineProps({
  title: { type: String, default: null },
  value: { type: Object, default: null },
  query: { type: Object, default: null },
  chip: { type: Boolean, default: false },
  iconShown: { type: Boolean, default: false },
  docUrl: { type: String, default: null }
});

const gradientColor = useGradientColor();
const isCopied = ref(false);

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.value);
    isCopied.value = true;
    
    // Reset button text after 2 seconds
    setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  } catch (error) {
    console.warn("Clipboard copy failed: ", error);
  }
};
</script>