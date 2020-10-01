<template>
  <v-container class="pa-0" fluid>
    <v-progress-linear
      v-if="loading"
      indeterminate
      size="64"
    />

    <items
      :items.sync="tags"
      :selected-items="selectedItems"
      :search="search"
      :limit="defaultLimit"
      @apply="apply"
      @cancel="cancel"
      @select="select"
    >
      <template v-slot:append-toolbar>
        <v-container>
          <v-row class="pt-2" justify="center">
            <v-date-picker v-model="dateFilter" no-title />
          </v-row>
        </v-container>

        <bulb-message>
          Selecting a date above will filter history events stored before
          midnight of the given date.
        </bulb-message>
      </template>


      <template v-slot:title="{ item }">
        <v-list-item-title
          v-if="item.title"
          :title="item.title"
        >
          {{ item.title }}
        </v-list-item-title>
        <v-list-item-title
          v-else
          :title="'No tag name is specified for this storage. Use the ' +
            '\'--tag\' option to specify a tag name for a storage at the ' +
            '\'CodeChecker store\' command.'"
        >
          Storage without a named tag
        </v-list-item-title>

        <v-list-item-subtitle :title="`Stored on ${item.time}`">
          {{ item.time }}
        </v-list-item-subtitle>
      </template>

      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>
    </items>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import { endOfDay, parse } from "date-fns";

import { ccService, handleThriftError } from "@cc-api";
import { DateInterval, ReportFilter } from "@cc/report-server-types";

import BulbMessage from "@/components/BulbMessage";
import DateMixin from "@/mixins/date.mixin";
import BaseFilterMixin from "./BaseFilter.mixin";
import Items from "./SelectOption/Items";

export default {
  name: "BaselineTagItems",
  components: { BulbMessage, Items },
  mixins: [ BaseFilterMixin, DateMixin ],
  props: {
    runId: { type: Number, required: true },
    selectedItems: { type: Array, default: null },
    limit: { type: Number, required: true }
  },
  data() {
    return {
      loading: false,
      search: {
        placeHolder : "Search by tag name...",
        filterItems: this.filterItems
      },
      tags: [],
      dateFilter: null,
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
    },

    async dateFilter() {
      this.tags = await this.fetchTags(this.filterOpt);
    }
  },

  async mounted() {
    this.tags = await this.fetchTags(this.filterOpt);
  },

  methods: {
    async getRunTagFilter() {
      const query = this.filterOpt.query;

      if (!query && !this.dateFilter)
        return null;

      let stored = null;
      if (this.dateFilter) {
        const date = parse(this.dateFilter, "yyyy-MM-dd", new Date());
        const midnight = endOfDay(date);

        stored = new DateInterval({
          before: this.getUnixTime(midnight)
        });
      }

      const tags =
        await ccService.getTags([ this.runId ], null, query, stored);

      return tags.map(t => t.id.toNumber());
    },

    async fetchTags(opt={}) {
      this.loading = true;
      this.filterOpt = opt;

      const reportFilter = new ReportFilter(this.reportFilter);
      const limit = opt.limit || this.limit;
      const offset = 0;

      reportFilter.runTag = await this.getRunTagFilter();

      return new Promise(resolve => {
        ccService.getClient().getRunHistoryTagCounts([ this.runId ],
          reportFilter, null, limit, offset, handleThriftError(res => {
            resolve(res.map(tag => {
              const id = tag.id.toNumber();
              const time = this.$options.filters.prettifyDate(tag.time);
              return {
                id,
                runName: tag.runName,
                runId: tag.runId.toNumber(),
                tagName: tag.name || time,
                time: time,
                title: tag.name,
                count: tag.count.toNumber()
              };
            }));

            this.loading = false;
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

<style lang="scss" scoped>
::v-deep .v-date-picker-table {
  height: 210px;
}
</style>
