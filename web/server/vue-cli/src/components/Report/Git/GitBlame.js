import Vue from "vue";
import { parse } from "date-fns";

import { ccService, handleThriftError } from "@cc-api";

import GitBlameLine from "./GitBlameLine";
const GitBlameLineClass = Vue.extend(GitBlameLine);

function getCommitColor(commit, minDate, maxDate) {
  const currTime = commit.committedDateTime;
  const commitHeat = (currTime - minDate) / (maxDate - minDate);

  // Convert to rgb.
  const [ r, g, b ] = [
    Math.round(128 + (1 - commitHeat) * 127),
    Math.round(128 +      commitHeat  * 127),
    128
  ];

  return `rgb(${r}, ${g}, ${b})`;
}

function getCommits(blameInfo, minDate, maxDate) {
  const commits = blameInfo.commits;
  const blame = blameInfo.blame;

  return blame.reduce((acc, curr) => {
    const commit = commits[curr.commitHash];
    if (!commit.color)
      commit.color = getCommitColor(commit, minDate, maxDate);

    acc[curr.startLine] = commit;
    acc[curr.startLine].hexsha = curr.commitHash;

    for (let i = curr.startLine + 1; i <= curr.endLine; ++i) {
      acc[i] = null;
    }

    return acc;
  }, {});
}

function getBlameInfo(fileId) {
  return new Promise(res => {
    ccService.getClient().getBlameInfo(fileId, handleThriftError(blameInfo =>
      res(blameInfo)));
  });
}

export default {
  data() {
    return {
      editor: null,
      gutterID: "blame-gutter",
      gutterMarkers: {},
      commits: {},
      blameInfo: null,
      sourceFile: null,
    };
  },
  methods: {
    hideBlameView() {
      return new Promise(res => {
        this.resetBlameBiew();

        this.editor.clearGutter(this.gutterID);
        this.editor.setOption("gutters", []);
        this.editor.setOption("lineNumbers", true);

        this.$nextTick(() => {
          this.editor.refresh();
          res();
        });
      });
    },

    resetBlameBiew() {
      this.editor.off("viewportChange", this.onViewportChange);
      this.gutterMarkers = {};
    },

    setGutterMarker(from, to) {
      this.editor.operation(() => {
        let lastCommitColor = null;
        for (let i = from; i >= 0; --i) {
          const commit = this.commits[i];
          if (commit) {
            lastCommitColor = commit.color;
            break;
          }
        }

        for (let i = from; i < to; ++i) {
          const commit = this.commits[i + 1];
          if (commit)
            lastCommitColor = commit.color;

          // If the marker already exists we can skip adding it again.
          if (this.gutterMarkers[i])
            continue;

          const widget = new GitBlameLineClass({
            propsData: {
              number: i + 1,
              commit,
              color: lastCommitColor,
              remoteUrl: this.sourceFile.remoteUrl,
              trackingBranch: this.sourceFile.trackingBranch
            }
          });

          // This is needed otherwise it will throw an error.
          widget.$vuetify = this.$vuetify;

          widget.$mount();

          this.editor.setGutterMarker(i, this.gutterID, widget.$el);
          this.gutterMarkers[i] = true;
        }
      });

      this.$nextTick(() => this.editor.refresh());
    },

    onViewportChange(cm, from, to) {
      this.setGutterMarker(from, to);
    },

    async loadBlameView() {
      this.blameInfo = await getBlameInfo(this.sourceFile.fileId);
      if (!this.blameInfo)
        return;

      this.resetBlameBiew();
      this.editor.setOption("gutters", [ this.gutterID ]);
      this.editor.setOption("lineNumbers", false);

      let maxDate = null;
      let minDate = Infinity;
      Object.values(this.blameInfo.commits).forEach(commit => {
        const currTime = parse(
          commit.committedDateTime, "yyyy-MM-dd HH:mm:ssXXX", new Date());

        if (currTime > maxDate) maxDate = currTime;
        if (currTime < minDate) minDate = currTime;

        commit.committedDateTime = currTime;
      });

      if (minDate === maxDate)
        --minDate; // This makes one-commit files green.

      this.commits = getCommits(this.blameInfo, minDate, maxDate);

      // Initalize the gutter markers.
      const { from, to } = this.editor.getViewport();
      this.setGutterMarker(from, to);

      // Add gutter markers on viewport change event.
      this.editor.on("viewportChange", this.onViewportChange);

      this.$router.replace({
        query: {
          ...this.$route.query,
          "view": "blame"
        }
      }).catch(() => {});
    }
  }
};
