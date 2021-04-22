<template>
  <v-dialog
    v-model="dialog"
    content-class="check-command"
    max-width="80%"
    scrollable
  >
    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Check commands

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-container class="pa-0 pt-2">
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-for="cmd in checkCommands"
            :key="cmd"
            class="check-command mb-2"
            v-html="cmd"
          />
        </v-container>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";

export default {
  name: "CheckCommandDialog",
  props: {
    value: { type: Boolean, default: false },
    runId: { type: Object, default: () => null },
    runHistoryId: { type: Object, default: () => null }
  },

  data() {
    return {
      checkCommands: [],
      enabledCheckerRgx: new RegExp("^(--enable|-e[= ]*)", "i"),
      disabledCheckerRgx: new RegExp("^(--disable|-d[= ]*)", "i"),
    };
  },

  computed: {
    dialog: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit("update:value", val);
      }
    }
  },

  watch: {
    runId() {
      this.getCheckCommands();
    },
    runHistoryId() {
      this.getCheckCommands();
    }
  },

  mounted() {
    this.getCheckCommands();
  },

  methods: {
    highlightOptions(cmd) {
      return cmd.split(" ").map(param => {
        if (!param.startsWith("-")) {
          return param;
        }

        const classNames = [ "param" ];
        if (this.enabledCheckerRgx.test(param)) {
          classNames.push("enabled-checkers");
        } else if (this.disabledCheckerRgx.test(param)) {
          classNames.push("disabled-checkers");
        } else if (param.startsWith("--ctu")) {
          classNames.push("ctu");
        } else if (param.startsWith("--stats")) {
          classNames.push("statistics");
        }

        return `<span class="${classNames.join(" ")}">${param}</span>`;
      }).join(" ");
    },

    getCheckCommands() {
      if (!this.dialog || (!this.runId && !this.runHistoryId)) return;

      this.checkCommands = [];
      ccService.getClient().getCheckCommand(this.runHistoryId, this.runId,
        handleThriftError(cmd => {
          const checkCmd =
            cmd?.replace("multiple analyze calls:", "") || "Unavailable!";

          this.checkCommands = checkCmd.split(";").map(cmd =>
            this.highlightOptions(cmd)
          );
        }));
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .check-command {
  border: 1px solid grey;
  padding: 4px;

  .param {
    background-color: rgba(0, 0, 0, 0.15);
    font-weight: bold;
    padding-left: 2px;
    padding-right: 2px;
  }

  .enabled-checkers {
    background-color: rgba(0, 142, 0, 0.15);
  }

  .disabled-checkers {
    background-color: rgba(142, 0, 0, 0.15);
  }

  .ctu, .statistics {
    background-color: rgba(0, 0, 142, 0.15);
  }
}
</style>
