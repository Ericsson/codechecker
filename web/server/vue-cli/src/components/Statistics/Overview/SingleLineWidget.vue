<template>
  <v-card :loading="loading" flat>
    <v-container>
      <v-row>
        <v-col cols="auto">
          <v-avatar :color="color" size="64" tile>
            <v-icon dark size="48">
              {{ icon }}
            </v-icon>
          </v-avatar>
        </v-col>
        <v-col class="text-center">
          <div class="subtitle grey--text text-uppercase">
            {{ label }}

            <tooltip-help-icon>
              <slot name="help" />
            </tooltip-help-icon>
          </div>
          <div class="text-h3 font-weight-bold">
            <slot name="value" :value="value">
              {{ value }}
            </slot>

            <slot name="append-value" />
          </div>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import TooltipHelpIcon from "@/components/TooltipHelpIcon";

export default {
  name: "SingleLineWidget",
  components: { TooltipHelpIcon },
  props: {
    icon: { type: String, required: true },
    color: { type: String, required: true },
    label: { type: String, required: true },
    helpMessage: { type: String, default: null },
    bus: { type: Object, required: true },
    getValue: { type: Function, required: true }
  },
  data() {
    return {
      loading: false,
      value: null
    };
  },
  activated() {
    this.bus.$on("refresh", () => this.fetchValue());
  },
  methods: {
    async fetchValue() {
      this.loading = true;
      this.value = await this.getValue();
      this.loading = false;
    }
  }
};
</script>

<style lang="scss" scoped>
.v-card {
  border: thin solid rgba(0, 0, 0, 0.12);
}
</style>
