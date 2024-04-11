import { ccService, handleThriftError } from "@cc-api";
import {
  AnalysisInfoFilter,
  RunFilter,
  RunHistoryFilter
} from "@cc/report-server-types";
import VersionMixin from "../version.mixin";

const GroupKeys = Object.freeze({
  NoGroup: "__N",
  AnalyzerTotal: "__S"
});

const CountKeys = Object.freeze({
  Enabled: 0,
  Disabled: 1,
  Total: 2
});

const CheckerInfoAvailability = Object.freeze({
  Available: 0,
  Unloaded: 1,
  UnknownReason: 2,
  RunHistoryStoredWithOldVersionPre_v6_24: 3,
  ReportIdToAnalysisInfoIdQueryNontrivialOverAPI: 4,
});

function decideNegativeCheckerStatusAvailability(
  analysisInfo, runId, runHistoryId, reportId) {
  if (
    (analysisInfo.checkerInfoAvailability !==
      CheckerInfoAvailability.UnknownReason) ||
    (!runId && !runHistoryId && !reportId)
  ) {
    return;
  }

  if (runId && !runHistoryId) {
    const filter = new RunFilter({
      ids: [ runId ]
    });
    ccService.getClient().getRunData(filter, null, null, null,
      handleThriftError(runDataList => {
        if (runDataList.length !== 1) return;

        setCheckerStatusUnavailableDueToVersion(
          analysisInfo,
          runDataList[0].codeCheckerVersion);
      }));
  } else if (runId && runHistoryId) {
    const filter = new RunHistoryFilter({
      tagNames: [],
      tagIds: [ runHistoryId ]
    });
    ccService.getClient().getRunHistory([ runId ], 1, 0,
      filter, handleThriftError(runHistoryDataList => {
        if (runHistoryDataList.length !== 1) return;

        setCheckerStatusUnavailableDueToVersion(
          analysisInfo,
          runHistoryDataList[0].codeCheckerVersion);
      }));
  } else if (reportId) {
    analysisInfo.checkerInfoAvailability = CheckerInfoAvailability.
      ReportIdToAnalysisInfoIdQueryNontrivialOverAPI;
  }
}

function setCheckerStatusUnavailableDueToVersion(analysisInfo, ccVersion) {
  ccVersion = VersionMixin.methods.prettifyCCVersion(ccVersion);
  if (!ccVersion) return false;
  analysisInfo.codeCheckerVersion = ccVersion;

  if (VersionMixin.methods.isNewerOrEqualCCVersion(ccVersion, "6.24")) {
    return false;
  }
  analysisInfo.checkerInfoAvailability =
    CheckerInfoAvailability.RunHistoryStoredWithOldVersionPre_v6_24;
  return true;
}

function getTopLevelCheckGroup(analyzerName, checkerName) {
  const clangTidyClangDiagnostic = checkerName.split("clang-diagnostic-");
  if (
    clangTidyClangDiagnostic.length > 1 && clangTidyClangDiagnostic[0] === ""
  ) {
    // Unfortunately, this is historically special...
    return "clang-diagnostic";
  }

  const splitDot = checkerName.split(".");
  if (splitDot.length > 1) {
    return splitDot[0];
  }

  const splitHyphen = checkerName.split("-");
  if (splitHyphen.length > 1) {
    if (splitHyphen[0] === analyzerName) {
      // cppcheck-PointerSize -> <NoGroup>
      // gcc-fd-leak          -> "fd"
      return splitHyphen.length >= 3 ? splitHyphen[1] : GroupKeys.NoGroup;
    }
    // bugprone-easily-swappable-parameters -> "bugprone"
    return splitHyphen[0];
  }

  return GroupKeys.NoGroup;
}

function mergeReduceCheckerStatuses(accumulator, inCheckerDict) {
  for (const [ analyzer, checkerList ] of Object.entries(inCheckerDict)) {
    if (!accumulator[analyzer]) {
      accumulator[analyzer] = {};
    }

    for (const [ checkerName, checkerInfo ] of Object.entries(checkerList)) {
      if (!accumulator[analyzer][checkerName]) {
        accumulator[analyzer][checkerName] = {
          enabled: false
        };
      }

      accumulator[analyzer][checkerName].enabled =
        accumulator[analyzer][checkerName].enabled || checkerInfo.enabled;
    }
  }

  return accumulator;
}

class AnalysisInfo {
  GroupKeys() { return GroupKeys; }
  CountKeys() { return CountKeys; }
  CheckerInfoAvailability() { return CheckerInfoAvailability; }

  constructor() {
    this.cmds = [];
    this.checkers = {};

    this.codeCheckerVersion = "0";
    this.checkerInfoAvailability = CheckerInfoAvailability.Unloaded;
    this.analyzers = [];
    this.checkersGroupedAndSorted = {};
    this.checkerGroupCounts = {};
  }

  populateAnalyzers() {
    this.analyzers = Object.keys(this.checkers).sort();
  }

  groupAndCountCheckers() {
    if (Object.keys(this.checkersGroupedAndSorted).length) {
      return this.checkersGroupedAndSorted;
    }

    var checkersGrouped = {};
    for (const [ analyzer, checkerList ] of Object.entries(this.checkers)) {
      if (!checkersGrouped[analyzer]) {
        checkersGrouped[analyzer] = {};
      }

      for (const [ checkerName, checkerInfo ] of Object.entries(checkerList)) {
        const groupForChecker = getTopLevelCheckGroup(analyzer, checkerName);
        if (!checkersGrouped[analyzer][groupForChecker]) {
          checkersGrouped[analyzer][groupForChecker] = {};
        }

        checkersGrouped[analyzer][groupForChecker][checkerName] = checkerInfo;
      }
    }

    this.checkersGroupedAndSorted = Object.fromEntries(this.analyzers.map(
      analyzer => [ analyzer,
        Object.fromEntries(
          Object.keys(checkersGrouped[analyzer]).sort().map(
            group => [ group,
              Object.keys(checkersGrouped[analyzer][group]).sort().map(
                checkerName => [ checkerName,
                  checkersGrouped[analyzer][group][checkerName]
                ])
            ])
        )
      ]));

    this.checkerGroupCounts = Object.fromEntries(this.analyzers.map(
      analyzer => [ analyzer,
        Object.fromEntries(
          Object.keys(this.checkersGroupedAndSorted[analyzer]).map(
            group => [ group, [
              // [CountKeys.Enabled]:
              Object.keys(this.checkersGroupedAndSorted[analyzer][group])
                .map(checker =>
                  this.checkersGroupedAndSorted[analyzer][group][checker][1]
                    .enabled ? 1 : 0)
                .reduce((a, b) => a + b, 0),
              /* [CountKeys.Disabled]: */ -1, // Will be updated later!
              // [CountKeys.Total]:
              Object.keys(
                this.checkersGroupedAndSorted[analyzer][group]
              ).length
            ]
            ]))
      ]));
    Object.keys(this.checkerGroupCounts).map(analyzer =>
      Object.keys(this.checkerGroupCounts[analyzer]).map(group => {
        this.checkerGroupCounts[analyzer][group][CountKeys.Disabled] =
          this.checkerGroupCounts[analyzer][group][CountKeys.Total] -
          this.checkerGroupCounts[analyzer][group][CountKeys.Enabled];
      }));
    Object.keys(this.checkerGroupCounts).map(analyzer => {
      const sum = Object.values(this.checkerGroupCounts[analyzer])
        .reduce((as, bs) => [
          as[CountKeys.Enabled]  + bs[CountKeys.Enabled],
          as[CountKeys.Disabled] + bs[CountKeys.Disabled],
          as[CountKeys.Total]    + bs[CountKeys.Total]
        ]);
      this.checkerGroupCounts[analyzer][GroupKeys.AnalyzerTotal] = sum;
    });

    return this.checkersGroupedAndSorted;
  }
}

const AnalysisInfoHandlingAPIMixin = {
  methods: {
    loadAnalysisInfo(runId, runHistoryId, reportId) {
      const analysisInfoFilter = new AnalysisInfoFilter({
        // Query a run's analysis info only if a run history ID is not explicit.
        runId: (!runHistoryId ? runId : null),

        runHistoryId: runHistoryId,
        reportId: reportId
      });
      const limit = null;
      const offset = 0;

      return new Promise(resolve => {
        ccService.getClient()
          .getAnalysisInfo(analysisInfoFilter, limit, offset,
            handleThriftError(aiResult => {
              var analysisInfo = new AnalysisInfo();
              analysisInfo.cmds = aiResult.map(r => r.analyzerCommand);
              analysisInfo.checkers = aiResult.map(r => r.checkers)
                .reduce(mergeReduceCheckerStatuses, {});

              if (Object.keys(analysisInfo.checkers).length) {
                analysisInfo.checkerInfoAvailability =
                  CheckerInfoAvailability.Available;
              } else {
                analysisInfo.checkerInfoAvailability =
                  CheckerInfoAvailability.UnknownReason;
              }

              analysisInfo.populateAnalyzers();

              resolve(analysisInfo);
            }));
      });
    },
  },
};

export {
  AnalysisInfo,
  AnalysisInfoHandlingAPIMixin as default,
  CheckerInfoAvailability,
  CountKeys,
  GroupKeys,
  decideNegativeCheckerStatusAvailability,
  setCheckerStatusUnavailableDueToVersion
};
