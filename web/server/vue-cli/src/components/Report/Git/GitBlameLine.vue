<template>
  <div
    :class="[
      'blame-line',
      commit ? 'blame-line-full' : undefined
    ]"
  >
    <v-menu
      v-if="commit"
      :close-on-content-click="false"
      :close-delay="200"
      :nudge-width="200"
      :max-width="400"
      open-on-hover
      offset-x
    >
      <template v-slot:activator="{ props: bindProps }">
        <component
          v-bind="bindProps"
          :is="'span'"
          class="blame-commit-info"
        >
          <span class="git-avatar mx-1">
            <v-avatar
              :color="strToColor(commit.author.name)"
              size="15"
            >
              <span class="white--text">
                {{ avatarLabel }}
              </span>
            </v-avatar>
          </span>

          <div class="git-message" :title="commit.summary">
            {{ commit.summary }}
          </div>

          <div class="git-time" :title="commit.committedDateTime">
            on {{ date }}
          </div>
        </component>
      </template>

      <v-card>
        <v-list>
          <v-list-item three-line>
            <template v-slot:prepend>
              <v-avatar
                :color="strToColor(commit.author.name)"
              >
                <span class="white--text">
                  {{ avatarLabel }}
                </span>
              </v-avatar>
            </template>

            <v-list-item-title class="font-weight-bold">
              {{ commit.summary }}
            </v-list-item-title>

            <v-list-item-subtitle
              :title="commit.hexsha"
            >
              <a :href="remoteCommitUrl" target="_blank">
                <span class="text--blue font-weight-bold">
                  #{{ hexsha }}
                </span>
              </a>
              <span :title="`Tracking branch: ${trackingBranch}`">
                ({{ truncate(trackingBranch, 20) }})
              </span>
            </v-list-item-subtitle>

            <v-list-item-subtitle>
              <span class="text--primary">
                {{ commit.author.name }}
              </span>
              ({{ commit.author.email }})
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <v-divider />

        <!-- eslint-disable vue/no-v-html -->
        <div class="pa-4" v-html="message" />
      </v-card>
    </v-menu>

    <span
      v-else
      class="blame-commit-info"
    >
      &nbsp;
    </span>

    <span
      class="blame-line-number"
      :style="{'background-color': color }"
    >
      {{ number }}
    </span>
  </div>
</template>

<script setup>
import { useStrToColor } from "@/composables/useStrToColor";
import { format } from "date-fns";
import { computed } from "vue";

const props = defineProps({
  commit: { type: Object, default: null },
  number: { type: Number, required: true },
  color: { type: String, required: true },
  remoteUrl: { type: String, default: null },
  trackingBranch: { type: String, default: null }
});

const { strToColor } = useStrToColor();

const remoteCommitUrl = computed(() => {
  return props.remoteUrl?.replace("$commit", props.commit.hexsha);
});

const avatarLabel = computed(() => {
  return props.commit.author.name.charAt(0).toUpperCase();
});

const date = computed(() => {
  return format(props.commit.committedDateTime, "yyyy-MM-dd");
});

const message = computed(() => {
  return props.commit.message.replace(/(?:\r\n|\r|\n)/g, "<br>");
});

const hexsha = computed(() => {
  return props.commit.hexsha.substring(0, 8);
});

function truncate(text, length) {
  if (!text) return "";
  if (text.length <= length) return text;
  return text.substring(0, length) + "...";
}
</script>

<style lang="scss" scoped>
.blame-line-full {
  border-top: 1px solid #bdbaba;
}

.blame-line {
  .blame-commit-info {
    display: inline-block;
    width: 330px;
    min-width: 330px;
    max-width: 330px;

    .git-avatar {
      float: left;
      color: white;
    }

    .git-message {
      max-width: 180px;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      display: inline-block;
      cursor: pointer;
    }

    .git-time {
      color: #6a737d;
      float: right;
      padding-right: 5px;
    }
  }

  .blame-line-number {
    min-width: 50px;
    text-align: right;
    padding-right: 10px;
    padding-left: 10px;
    color: #4e524e;
    font-weight: bold;
    position: absolute;
    right: 0;
  }
}
</style>