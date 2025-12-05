import { parse } from "date-fns";
import { getCurrentInstance, h, ref, render, toRaw } from "vue";
import { useRoute, useRouter } from "vue-router";
import { GutterMarker, gutter } from "@codemirror/view";
import { Compartment } from "@codemirror/state";

import { ccService, handleThriftError } from "@cc-api";
import GitBlameLine from "@/components/Report/Git/GitBlameLine.vue";

function getCommitColor(commit, minDate, maxDate) {
  const currTime = commit.committedDateTime;
  const commitHeat = (currTime - minDate) / (maxDate - minDate);

  const [ r, g, b ] = [
    Math.round(128 + (1 - commitHeat) * 127),
    Math.round(128 + commitHeat * 127),
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
  return new Promise(resolve => {
    ccService.getClient().getBlameInfo(
      fileId,
      handleThriftError(blameInfo => {
        resolve(blameInfo);
      },
      error => {
        console.warn("ERROR:", error);
        resolve(null);
      })
    );
  });
}

class BlameMarker extends GutterMarker {
  constructor(
    { lineNum, commit, color, remoteUrl, trackingBranch },
    appContext
  ) {
    super();
    this.props = {
      lineNum,
      commit,
      color,
      remoteUrl,
      trackingBranch
    };
    this.appContext = appContext;
    this.container = null;
  }

  toDOM() {
    this.container = document.createElement("div");
    const vnode = h(GitBlameLine, this.props);
    vnode.appContext = this.appContext;
    render(vnode, this.container);
    return this.container;
  }

  destroy() {
    if (this.container) {
      render(null, this.container);
    }
  }
}

export function useGitBlame(editor, sourceFile) {
  const router = useRouter();
  const route = useRoute();
  const instance = getCurrentInstance();
  const appContext = instance?.appContext;

  if (!appContext) {
    console.warn(
      "No valid appContext found; useGitBlame must be used inside setup()!"
    );
  }

  const commits = ref({});
  const blameInfo = ref(null);
  const blameEnabled = ref(false);
  const blameCompartment = new Compartment();
  const createGitBlame = config => new BlameMarker(config, appContext);

  const blameGutter = gutter({
    class: "blame-gutter",
    lineMarker(view, line) {
      if (!blameEnabled.value) {
        return null;
      }
      if (!view?.state?.doc || !line?.from) {
        return null;
      }

      const doc = view.state.doc;
      if (line.from < 0 || line.from > doc.length) {
        return null;
      }

      const lineNum = doc.lineAt(line.from).number;
      const commit = commits.value[lineNum];

      let lastCommitColor = null;
      for (let i = lineNum - 1; i >= 1; i--) {
        const c = commits.value[i];
        if (c) {
          lastCommitColor = c.color;
          break;
        }
      }

      const color = commit ? commit.color : lastCommitColor;
      
      return new BlameMarker(
        {
          lineNum,
          commit,
          color,
          remoteUrl: sourceFile.value?.remoteUrl,
          trackingBranch: sourceFile.value?.trackingBranch
        },
        appContext
      );
    }
  });

  const hideBlameView = () => {
    return new Promise(res => {
      blameEnabled.value = false;
      
      if (editor.value) {
        editor.value.dispatch({
          effects: blameCompartment.reconfigure([])
        });
      }

      router.replace({
        query: {
          ...route.query,
          "view": undefined
        }
      }).catch(() => {});

      res();
    });
  };

  const loadBlameView = async () => {
    if (!sourceFile.value?.fileId) return;

    blameInfo.value = await getBlameInfo(toRaw(sourceFile.value.fileId));
    if (!blameInfo.value) {
      return;
    }

    let maxDate = null;
    let minDate = Infinity;
    Object.values(blameInfo.value.commits).forEach(commit => {
      const currTime = parse(
        commit.committedDateTime, "yyyy-MM-dd HH:mm:ssXXX", new Date());

      if (currTime > maxDate) maxDate = currTime;
      if (currTime < minDate) minDate = currTime;

      commit.committedDateTime = currTime;
    });

    if (minDate === maxDate)
      --minDate;

    commits.value = getCommits(blameInfo.value, minDate, maxDate);
    blameEnabled.value = true;

    if (editor.value) {
      editor.value.dispatch({
        effects: blameCompartment.reconfigure([ blameGutter ])
      });
    }

    router.replace({
      query: {
        ...route.query,
        "view": "blame"
      }
    }).catch(() => {});
  };

  return {
    blameInfo,
    commits,
    hideBlameView,
    loadBlameView,
    blameGutter,
    blameCompartment,
    createGitBlame
  };
}
