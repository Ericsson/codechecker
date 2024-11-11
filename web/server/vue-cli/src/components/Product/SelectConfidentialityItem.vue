<template>
  <div>
    <v-avatar
      left
      :size="16"
    >
      <confidentiality-icon
        :value="confidentialityFromStringToCode(value)"
        small
      />
    </v-avatar>
    {{ value }}
  </div>
</template>

<script>
import { ConfidentialityMixin } from "@/mixins";
import { ConfidentialityIcon } from "@/components/Icons";

export default {
  name: "SelectConfidentialityItem",
  components: {
    ConfidentialityIcon
  },
  mixins: [ ConfidentialityMixin ],
  props: {
    value: { type: String, required: true }
  }
};
</script>

