<template>
  <v-alert
    :outlined="show"
    :color="color"
    :text="text"
    icon="mdi-alert"
    class="mt-2"
  >
    <span
      v-if="!show"
      @click="display"
    >
      Columns containing sum values may be wrong in unique mode.
      <span class="link">(More)</span>
    </span>
    <span v-if="show">
      It is possible that a report type (i.e. set of reports sharing the same
      hash) is assigned different review status in different runs. For example,
      such a report can be both <i>Unreviewed</i> and
      <i>Confirmed</i>, thus it is counted under both. However, a bug type is
      counted only once in <b>Outstanding reports</b>,
      <b>Suppressed reports</b> and <b>All reports</b> columns in
      <b>Unique reports</b> mode. In this case these summary columns don't add
      up the values of the corresponding review status columns.
      <span class="link" @click="display">
        (Less)
      </span>
    </span>
  </v-alert>
</template>

<script>
export default {
  name: "UniqueStatWarning",
  data() {
    return {
      color: "",
      show: false,
      text: false
    };
  },
  methods: {
    display() {
      this.show = !this.show;
      this.text = !this.text;
      this.color = this.show ? "deep-orange" : "";
    }
  }
};
</script>

<style lang="scss" scoped>
.link:hover {
  cursor: pointer;
  text-decoration: underline;
}

.v-alert {
  font-size: 14px
}
</style>