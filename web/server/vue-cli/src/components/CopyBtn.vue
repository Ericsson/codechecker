<template>
  <v-tooltip
    v-model="copyInProgress"
    color="black"
    right
  >
    <template v-slot:activator="{}">
      <v-btn icon x-small @click="copy">
        <v-icon v-if="copyInProgress" color="green">
          mdi-check
        </v-icon>

        <v-icon v-else>
          mdi-content-paste
        </v-icon>    
      </v-btn>
    </template>
    Copied!
  </v-tooltip>
</template>

<script>
function writeToClipboard(str) {
  const el = document.createElement("textarea");
  el.value = str;

  document.body.appendChild(el);
  el.select();

  document.execCommand("copy");

  document.body.removeChild(el);
}

export default {
  name: "CopyBtn",
  props: {
    value: { type: String, required: true }
  },
  data() {
    return {
      copyInProgress: false
    };
  },
  methods: {
    copy() {
      this.copyInProgress = true;

      writeToClipboard(this.value);

      setTimeout(() => this.copyInProgress = false, 1000);
    }
  }
};
</script>
