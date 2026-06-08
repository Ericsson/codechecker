<template>
  <div>
    <v-avatar
      left
      :size="16"
    >
      <review-status-icon
        :status="value"
        :size="16"
      />
    </v-avatar>

    <slot name="label">
      {{ label }}
    </slot>
  </div>
</template>

<script>
import { ReviewStatusIcon } from "@/components/Icons";
import { ReviewStatusMixin } from "@/mixins";

// TODO: this is the same as SelectReviewStatusItem component.
export default {
  name: "ReviewStatusLabel",
  components: {
    ReviewStatusIcon
  },
  mixins: [ ReviewStatusMixin ],
  props: {
    value: { type: Number, required: true }
  },
  computed: {
    label() {
      return this.reviewStatusFromCodeToString(this.value);
    }
  }
};
</script>
