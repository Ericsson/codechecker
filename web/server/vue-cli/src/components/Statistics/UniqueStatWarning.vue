<template>
  <v-alert
    text
    outlined
    color="deep-orange"
    icon="mdi-alert"
    class="mt-2"
  >
    It is possible that a report type (i.e. set of reports sharing the same
    hash) is assigned different review status in different runs. For example,
    such a report can be both <i>Unreviewed</i> and <i>Confirmed</i>, thus it
    is counted under both. However, a bug type is counted only once in
    <b>Outstanding reports</b>, <b>Suppressed reports</b> and
    <b>All reports</b> columns in <b>Unique reports</b> mode. In this case
    these summary columns don't add up the values of the corresponding review
    status columns.
  </v-alert>
</template>

<script>
export default {
  name: "UniqueStatWarning"
};
</script>
