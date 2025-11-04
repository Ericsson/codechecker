module.exports = {
  before(browser) {
    browser.resizeWindow(1600, 1000);

    const login = browser.page.login();

    const runs = browser.page.runs();

    login
      .navigate(runs.url())
      .loginAsRoot();

    browser.expect.url().to.equal(runs.url()).before(5000);

    runs.waitForElementVisible("@page", 10000);
  },

  after(browser) {
    browser.end();
  },

  "sort runs by run name" (browser) {
    const col = 3;
    const runsPage = browser.page.runs();

    runsPage.sortRuns(col, (data) => {
      return data.every((e, ind, a) =>
        !ind || a[ind - 1][col - 1] <= e[col - 1]);
    });
  },

  "sort runs by number of unresolved reports" (browser) {
    const col = 4;
    const runsPage = browser.page.runs();

    runsPage.sortRuns(col, (data) => {
      return data.every((e, ind, a) =>
        !ind || a[ind - 1][col - 1] <= e[col - 1]);
    });

    runsPage.sortRuns(col, (data) => {
      return data.every((e, ind, a) =>
        !ind || a[ind - 1][col - 1] >= e[col - 1]);
    });
  },

  "filter by run name" (browser) {
    const runName = "simple";
    const tag = "v0.0.9";
    const runsPage = browser.page.runs();
    const filterSection = runsPage.section.runFilterToolbar;

    filterSection.clearAndSetValue("@runName", runName);

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar")
      .assert.urlContains(`run=${runName}`)

    runsPage.getTableRows("@tableRows", (runs) => {
      browser.assert.ok(runs.length === 1);
      browser.assert.ok(runs[0][2].includes(tag));
    });
  },

  "show run description" (browser) {
    const description = "This is my updated run.";
    const runsPage = browser.page.runs();

    // Show the description
    runsPage
      .click("@showDescriptionBtn")
      .waitForElementVisible("@descriptionMenu")
      .assert.containsText("@descriptionMenu", description)

    // Close description tooltip.
    runsPage
      .click("@showDescriptionBtn")
      .waitForElementNotPresent("@descriptionMenu");
  },

  async "show check command of a run" (browser) {
    const checkCommand = "cli.py analyze";
    const runsPage = browser.page.runs();
    const dialogSection = runsPage.section.analysisInfoDialog;

    runsPage.click("@showAnalysisInfoBtn");

    runsPage.expect.section(dialogSection)
      .to.be.visible.before(5000);

    dialogSection.assert.containsText("@command", checkCommand);

    dialogSection.expect.element("@checkerStatuses")
      .to.be.present.before(5000);
    dialogSection.expect.element("@checkerStatusError")
      .to.not.be.present.before(5000);

    dialogSection.pause(1000);
    await (async () => {
      const analyzerPanelBtnSelector = ".analysis-info " +
        ".analyzer-checkers-panel" +
          ".v-expansion-panel" +
          ":not(.v-expansion-panel--active) " +
        "button";

      dialogSection.expect.element(analyzerPanelBtnSelector)
        .to.be.present.before(5000);

      const analyzerPanelBtns = await runsPage.api.findElements(
        analyzerPanelBtnSelector);
      analyzerPanelBtns.value.forEach(async btnId =>
        await runsPage.api.elementIdClick(btnId.getId()));

      dialogSection.expect.element(analyzerPanelBtnSelector)
        .to.not.be.present.before(5000);
    })();
    await (async () => {
      const checkerGroupPanelBtnSelector = ".analysis-info " +
        ".analyzer-checker-group-panel" +
          ".v-expansion-panel" +
          ":not(.v-expansion-panel--active) " +
        "button";

      dialogSection.expect.element(checkerGroupPanelBtnSelector)
        .to.be.present.before(5000);

      const checkerGroupPanelBtns = await runsPage.api.findElements(
        checkerGroupPanelBtnSelector);
      checkerGroupPanelBtns.value.forEach(async btnId =>
        await runsPage.api.elementIdClick(btnId.getId()));

      dialogSection.expect.element(checkerGroupPanelBtnSelector)
        .to.not.be.present.before(5000);
    })();
    dialogSection.pause(1000);

    const assertCheckerStatus = (analyzer, group, checker, enabled) => {
      const checkerSelector = ".analysis-info " +
        ".analyzer-checkers-panel[data-analyzer-name='" + analyzer + "'] " +
        (group === "" ? "" :
          ".analyzer-checker-group-panel[data-group-name='" + group +"'] ") +
        ".analysis-info-checker[data-checker-name='" + checker + "'] " +
        ".checker-" + (enabled ? "enabled" : "disabled");

      dialogSection.expect.element(checkerSelector).to.be.present.before(1000);
      dialogSection.expect.element(checkerSelector).text.to.equal(checker);
    };
    const assertChecker = (analyzer, group, checker) =>
      assertCheckerStatus(analyzer, group, checker, true);
    const assertNotChecker = (analyzer, group, checker) =>
      assertCheckerStatus(analyzer, group, checker, false);

    assertChecker("clangsa", "core", "core.DivideZero");
    assertChecker("clangsa", "cplusplus", "cplusplus.NewDelete");
    assertNotChecker("clangsa", "osx", "osx.cocoa.Loops");

    assertChecker("clang-tidy", "clang-diagnostic", "clang-diagnostic-switch");
    assertNotChecker("clang-tidy", "llvm", "llvm-header-guard");

    // Close analysis info dialog.
    dialogSection.pause(100).click("@closeBtn");

    runsPage.expect.section(dialogSection)
      .to.not.be.present.before(5000);
  },

  "open a run"(browser) {
    const runName = "simple";
    const runsPage = browser.page.runs();

    runsPage
      .click("@name")
      .pause(100)
      .assert.urlContains(`run=${runName}`)
      .assert.urlContains("review-status=Unreviewed")
      .assert.urlContains("review-status=Confirmed%20bug")
      .assert.urlContains("detection-status=New")
      .assert.urlContains("detection-status=Reopened")
      .assert.urlContains("detection-status=Unresolved")
      .waitForElementVisible("@page")
      .backToRunsPage();
  },

  "open run statistics"(browser) {
    const runName = "simple";
    const runsPage = browser.page.runs();

    runsPage
      .click("@showStatisticsBtn")
      .assert.urlContains("/statistics")
      .assert.urlContains(`run=${runName}`)
      .assert.urlContains("is-unique=on")
      .assert.urlContains("detection-status=New")
      .assert.urlContains("detection-status=Reopened")
      .assert.urlContains("detection-status=Unresolved")
      .waitForElementVisible("@page")
      .backToRunsPage();
  },

  "open run detection status"(browser) {
    const runName = "simple";
    const runsPage = browser.page.runs();

    runsPage
      .click("@openDetectionStatus")
      .assert.urlContains("/reports")
      .assert.urlContains(`run=${runName}`)
      .assert.urlContains("detection-status=")
      .waitForElementVisible("@page")
      .backToRunsPage();
  },

  "diff two runs" (browser) {
    const runsPage = browser.page.runs();
    const tbl = runsPage.section.table;
    const filterSection = runsPage.section.runFilterToolbar;

    filterSection.clearAndSetValue("@runName", "");

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");

    runsPage.assert.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled");

    tbl
      .click({ selector: "@baseline", index: 0 })
      .click({ selector: "@compareTo", index: 1 });

    runsPage
      .assert.not.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled")
      .click("@diffSelectedRunsBtn")
      .assert.urlContains("/reports")
      .assert.urlContains("run=")
      .assert.urlContains("newcheck=")
      .backToRunsPage();
  },

  "show run history" (browser) {
    const runName = "simple";
    const runsPage = browser.page.runs();
    const filterSection = runsPage.section.runFilterToolbar;
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    filterSection.clearAndSetValue("@runName", runName);

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar")
      .click("@expandBtn")

    runsPage.expect.section(expandedSection).to.be.visible.before(5000);
    expandedSection.expect.section(timelineSection).to.be.visible.before(5000);
  },

  "load more run history events" (browser) {
    const runsPage = browser.page.runs();
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    expandedSection.waitForElementVisible("@loadMoreBtn");

    timelineSection.api.elements("@historyEvent", ({result}) => {
      browser.assert.ok(result.length === 10);
    });

    expandedSection.click("@loadMoreBtn");
    expandedSection
      .pause(500)
      .waitForElementNotPresent("@loadMoreBtn");

    timelineSection.api.elements("@historyEvent", ({result}) => {
      browser.assert.ok(result.length > 10);
    });
  },

  "filter by run history tag" (browser) {
    const tagName = "v0.0.1";
    const runsPage = browser.page.runs();
    const filterSection = runsPage.section.runFilterToolbar;
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    // Scroll back to solve "Element is not clickable at point" problem in
    // chrome.
    browser.execute("scrollTo(0, 0)");

    filterSection.clearAndSetValue("@runTag", tagName);

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");

    runsPage.perform(() => {
      timelineSection.api.elements("@historyEvent", ({result}) => {
        browser.assert.ok(result.length === 1);
      });
    });

    // Clear run name and tag filter.
    filterSection.clearAndSetValue("@runTag", "");

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");
  },

  "open run history event" (browser) {
      const runsPage = browser.page.runs();
      const expandedSection = runsPage.section.expanded;
      const timelineSection = expandedSection.section.timeline;

      timelineSection.click({ selector: "@date", index: 0 });

      runsPage
        .assert.urlContains("/reports")
        .assert.urlContains("run-tag=")
        .backToRunsPage();
  },

  "open statistics of a run history event" (browser) {
    const runsPage = browser.page.runs();
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    timelineSection.click("@showStatisticsBtn");

    runsPage
      .assert.urlContains("/statistics")
      .assert.urlContains("run=")
      .assert.urlContains("run-tag=")
      .assert.urlContains("is-unique=on")
      .assert.urlContains("detection-status=New")
      .assert.urlContains("detection-status=Reopened")
      .assert.urlContains("detection-status=Unresolved")
      .waitForElementVisible("@page")
      .backToRunsPage();
  },

  "show check command of a run history event" (browser) {
      const checkCommand = "cli.py analyze";
      const runsPage = browser.page.runs();
      const expandedSection = runsPage.section.expanded;
      const timelineSection = expandedSection.section.timeline;
      const dialogSection = runsPage.section.analysisInfoDialog;

      timelineSection.click("@showAnalysisInfoBtn");

      runsPage.expect.section(dialogSection)
        .to.be.visible.before(5000);

      dialogSection.assert.containsText("@command", checkCommand);

      dialogSection.expect.element("@checkerStatuses")
        .to.be.present.before(5000);
      dialogSection.expect.element("@checkerStatusError")
        .to.not.be.present.before(5000);

      // Close analysis info dialog.
      dialogSection.click("@closeBtn");

      runsPage.expect.section(dialogSection)
        .to.not.be.present.before(5000);
  },

  "diff two run history events" (browser) {
    const runsPage = browser.page.runs();
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    runsPage.assert.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled");

    timelineSection
      .click({ selector: "@baseline", index: 0 })
      .click({ selector: "@compareTo", index: 1 });

      runsPage
        .assert.not.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled")
        .click("@diffSelectedRunsBtn")
        .assert.urlContains("/reports")
        .assert.urlContains("run-tag=")
        .assert.urlContains("run-tag-newcheck=")
        .backToRunsPage();
  },

  "diff a run and a run history event" (browser) {
    const runsPage = browser.page.runs();
    const tbl = runsPage.section.table;
    const expandedSection = runsPage.section.expanded;
    const timelineSection = expandedSection.section.timeline;

    runsPage.assert.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled");

    tbl.click({ selector: "@baseline", index: 0 })

    timelineSection
      .click({ selector: "@compareTo", index: 1 });

    runsPage
      .assert.not.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled")
      .click("@diffSelectedRunsBtn")
      .assert.urlContains("/reports")
      .assert.urlContains("run=")
      .assert.not.urlContains("run-tag=")
      .assert.urlContains("run-tag-newcheck=")
      .backToRunsPage();
  },

  "remove a run" (browser) {
    const runName = "remove";
    const runsPage = browser.page.runs();
    const filterSection = runsPage.section.runFilterToolbar;
    const tbl = runsPage.section.table;
    const removeDialog = runsPage.section.removeRunDialog;

    filterSection.clearAndSetValue("@runName", runName);

    runsPage
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar")
      .assert.urlContains(`run=${runName}`)

    runsPage
      .assert.cssClassPresent("@deleteSelectedRunsBtn", "v-btn--disabled");

    tbl.click({ selector: "@remove", index: 0 })

    runsPage
      .assert.not.cssClassPresent("@deleteSelectedRunsBtn", "v-btn--disabled");

    runsPage
      .click("@deleteSelectedRunsBtn")
      .expect.section("@removeRunDialog").to.be.visible.before(5000);

    runsPage.expect.element("@overlay").to.be.visible.before(5000);
    removeDialog.pause(100).click("@confirmBtn");

    runsPage.expect.section("@removeRunDialog")
      .to.not.be.present.before(5000);
  }
}
