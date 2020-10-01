<template>
  <items
    :items.sync="tags"
    :selected-items="selectedItems"
    :search="search"
    :limit="defaultLimit"
    @apply="apply"
    @cancel="cancel"
    @select="select"
  >
    <template v-slot:icon="{ item }">
      <slot name="icon" :item="item" />
    </template>
  </items>
</template>

<script>
import { mapState } from "vuex";
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import BaseFilterMixin from "./BaseFilter.mixin";
import Items from "./SelectOption/Items";

export default {
  name: "BaselineTagItems",
  components: { Items },
  mixins: [ BaseFilterMixin ],
  props: {
    runId: { type: Number, required: true },
    selectedItems: { type: Array, default: null },
    limit: { type: Number, required: true }
  },
  data() {
    return {
      loading: false,
      search: {
        placeHolder : "Search for run tags...",
        filterItems: this.filterItems
      },
      tags: [],
      filterOpt: {}
    };
  },
  computed: {
    ...mapState({
      reportFilter(state) {
        return state[this.namespace].reportFilter;
      }
    })
  },
  watch: {
    async runId() {
      this.tags = await this.fetchTags(this.filterOpt);
    }
  },

  async mounted() {
    this.tags = await this.fetchTags(this.filterOpt);
  },

  methods: {
    async getTagIds(runWithTagName) {
      const tags = await ccService.getTags(null, runWithTagName);
      return tags.map(t => t.id.toNumber());
    },

    async fetchTags(opt={}) {
      this.filterOpt = opt;

      const reportFilter = new ReportFilter(this.reportFilter);
      const limit = opt.limit || this.limit;
      const offset = 0;

      reportFilter.runTag = opt.query
        ? (await Promise.all(opt.query?.map(s => this.getTagIds(s)))).flat()
        : null;

      return new Promise(resolve => {
        ccService.getClient().getRunHistoryTagCounts([ this.runId ],
          reportFilter, null, limit, offset, handleThriftError(res => {
            resolve(res.map(tag => {
              const id = tag.id.toNumber();
              const name = tag.name || "N/A";
              const time = this.$options.filters.prettifyDate(tag.time);
              return {
                id,
                runName: tag.runName,
                runId: tag.runId.toNumber(),
                tagName: tag.name || time,
                title: `${name} (${time})`,
                count: tag.count.toNumber()
              };
            }));
          }));
      });
    },

    filterItems(value) {
      return this.fetchTags({ query: value ? [ `${value}*` ] : null });
    },

    apply() {
      this.$emit("apply");
    },

    select(selectedItems) {
      this.$emit("select", selectedItems);
    },

    cancel() {
      this.$emit("cancel");
    }
  }
};
</script>
