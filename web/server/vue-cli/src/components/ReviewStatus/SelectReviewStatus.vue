<template>
  <v-select
    v-model="reviewStatus"
    :items="items"
    :hide-details="true"
    :menu-props="{ contentClass: 'select-review-status-menu' }"
    :label="label"
    :clearable="clearable"
    :rules="rules"
    item-text="label"
    item-value="id"
    class="select-review-status small"
    height="0"
    flat
    dense
    outlined
    @change="onChange"
  >
    <template v-slot:selection="{ item }">
      <select-review-status-item :item="item" />
    </template>

    <template v-slot:item="{ item }">
      <select-review-status-item :item="item" />
    </template>
  </v-select>
</template>

<script>
import { ReviewStatus } from "@cc/report-server-types";
import { ReviewStatusMixin } from "@/mixins";
import { SelectReviewStatusItem } from "@/components/Report";

export default {
  name: "SelectReviewStatus",
  components: { SelectReviewStatusItem },
  mixins: [ ReviewStatusMixin ],
  props: {
    value: { type: Number, default: null },
    label: { type: String, default: "Select review status" },
    clearable: { type: Boolean, default: true },
    rules: { type: Array, default: () => [] }
  },
  data() {
    return {
      items: []
    };
  },
  computed: {
    reviewStatus: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("input", val);
      }
    }
  },
  created() {
    this.items = Object.values(ReviewStatus).map(id => {
      return {
        id: id,
        label: this.reviewStatusFromCodeToString(parseInt(id))
      };
    });
  },
  methods: {
    onChange() {
      this.$emit("change", this.value);
    }
  }
};
</script>
