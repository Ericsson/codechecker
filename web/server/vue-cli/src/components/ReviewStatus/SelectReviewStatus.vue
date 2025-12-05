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
import { computed, ref } from "vue";
import { ReviewStatusIcon } from "@/components/Icons";

const props = defineProps({
  modelValue: { type: Number, default: null },
  label: { type: String, default: "Select review status" },
  clearable: { type: Boolean, default: true },
  rules: { type: Array, default: () => [] }
});

const emit = defineEmits([ "update:modelValue", "change" ]);

const reviewStatus = useReviewStatus();
const items = ref(Object.values(ReviewStatus)
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
