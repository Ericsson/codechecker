<template>
  <v-card
    :loading="loading"
    flat
  >
    <v-container>
      <v-row
        align="center"
      >
        <v-col
          cols="auto"
        >
          <v-avatar
            :color="color"
            size="64"
            rounded="0"
            class="ma-2"
          >
            <v-icon
              size="48"
            >
              {{ icon }}
            </v-icon>
          </v-avatar>
        </v-col>
        <v-col
          class="text-center"
        >
          <div
            class="text-subtitle-1 text-grey text-uppercase"
          >
            {{ label }}

            <tooltip-help-icon>
              <slot name="help" />
            </tooltip-help-icon>
          </div>
          <div
            class="text-h3 font-weight-bold"
          >
            <slot
              name="value"
              :value="value"
            >
              {{ value }}
            </slot>

            <slot name="append-value" />
          </div>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script setup>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

defineProps({
  icon: { type: String, required: true },
  color: { type: String, required: true },
  label: { type: String, required: true },
  helpMessage: { type: String, default: null },
  bus: { type: Object, required: true },
  value: { type: Array, required: true },
  loading: { type: Boolean, default: false }
});

</script>

<style lang="scss" scoped>
.v-card {
  border: thin solid rgba(0, 0, 0, 0.12);
}
</style>
