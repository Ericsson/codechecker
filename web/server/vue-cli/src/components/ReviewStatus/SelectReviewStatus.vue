<template>
  <v-select
    v-model="reviewStatusValue"
    :items="items"
    :hide-details="true"
    :label="label"
    :clearable="clearable"
    :rules="rules"
    item-title="label"
    item-value="id"
    class="select-review-status small"
    density="compact"
    variant="outlined"
  >
    <template v-slot:selection="{ item }">
      <div class="d-flex align-center">
        <review-status-icon
          :status="item.value"
          :size="16"
          class="mx-2"
        />
        <span>{{ item.title }}</span>
      </div>
    </template>

    <template v-slot:item="{ item, props: itemProps }">
      <v-list-item
        v-bind="itemProps"
      >
        <template v-slot:prepend>
          <review-status-icon
            :status="item.raw.id"
            :size="16"
            class="mx-2"
          />
        </template>
      </v-list-item>
    </template>
  </v-select>
</template>

<script setup>
import { useReviewStatus } from "@/composables/useReviewStatus";
import { ReviewStatus } from "@cc/report-server-types";
import { computed } from "vue";
import { ReviewStatusIcon } from "@/components/Icons";

const props = defineProps({
  modelValue: { type: Number, default: null },
  label: { type: String, default: "Select review status" },
  clearable: { type: Boolean, default: true },
  rules: { type: Array, default: () => [] },
  // Hide the "Unreviewed" option (e.g. in forms where it is not a valid
  // value, such as when creating a review status rule).
  excludeUnreviewed: { type: Boolean, default: false }
});

const emit = defineEmits([ "update:modelValue", "change" ]);

const reviewStatus = useReviewStatus();
const items = computed(() => Object.values(ReviewStatus)
  .filter(id => !(props.excludeUnreviewed && id === ReviewStatus.UNREVIEWED))
  .map(id => ({
    id: id,
    label: reviewStatus.reviewStatusFromCodeToString(parseInt(id))
  }))
);

const reviewStatusValue = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit("update:modelValue", val);
  }
});
</script>
