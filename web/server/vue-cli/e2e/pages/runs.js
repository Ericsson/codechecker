const commands = {
  filterRuns(search, cb) {
    this.clearAndSetValue("@searchInput", search)
      .pause(500)  // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar")
      .assert.urlContains(`name=${search}`)

    this.getTableRows("@tableRows", cb);

    return this;
  },

  backToRunsPage() {
    this.api.back();

    return this
      .pause(500) // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");
  },

  openRun(name) {
    return this
      .click("@name")
      .assert.urlContains(`run=${name}`)
      .assert.urlContains("review-status=Unreviewed")
      .assert.urlContains("review-status=Confirmed%20bug")
      .assert.urlContains("detection-status=New")
      .assert.urlContains("detection-status=Reopened")
      .assert.urlContains("detection-status=Unresolved")
      .waitForElementVisible("@page");
  },

  openRunHistory(name) {
    return this
      .click("@showHistoryBtn")
      .assert.urlContains("/run-history")
      .assert.urlContains(`run=${name}`)
      .waitForElementVisible("@page");
  },

  openStatistics(name) {
    return this
      .click("@showStatisticsBtn")
      .assert.urlContains("/statistics")
      .assert.urlContains(`run=${name}`)
      .assert.urlContains("is-unique=on")
      .assert.urlContains("detection-status=New")
      .assert.urlContains("detection-status=Reopened")
      .assert.urlContains("detection-status=Unresolved")
      .waitForElementVisible("@page");
  },

  openDetectionStatus(name) {
    return this
      .click("@openDetectionStatus")
      .assert.urlContains("/reports")
      .assert.urlContains(`run=${name}`)
      .assert.urlContains("detection-status=")
      .waitForElementVisible("@page");
  },

  sortRuns(column, isSorted) {
    this
      .click(`th:nth-child(${column})`)
      .pause(500) // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");

    this.getTableRows("@tableRows", (data) => {
      this.api.assert.ok(isSorted(data), "runs are not sorted");
    });

    return this;
  },

  showDescription() {
    return this
      .click("@showDescriptionBtn")
      .waitForElementVisible("@descriptionMenu");
  },

  closeDescription() {
    return this
      .click("@showDescriptionBtn")
      .waitForElementNotPresent("@descriptionMenu");
  },

  showCheckCommand() {
    this.click("@showCheckCommandBtn", () => {
      this.expect.section("@checkCommandDialog").to.be.visible;
    });

    return this;
  },

  closeCheckCommand() {
    const section = this.section.checkCommandDialog;

    section.click("@closeBtn", () => {
      this.expect.section("@checkCommandDialog")
        .to.not.be.present.before(5000);
    });

    return this;
  },

  removeFirstRun() {
    this
      .assert.cssClassPresent("@deleteSelectedRunsBtn", "v-btn--disabled")
      .click("@removeRunCheckbox")
      .assert.not.cssClassPresent("@deleteSelectedRunsBtn", "v-btn--disabled")
      .click("@deleteSelectedRunsBtn");

    this.expect.section("@removeRunDialog").to.be.visible.before(5000);

    this.section.removeRunDialog.click("@confirmBtn");

    this.expect.section("@removeRunDialog")
      .to.not.be.present.before(5000);

    return this;
  },

  diffFirstTwoRuns() {
    this
      .assert.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled")
      .click("@firstRunToDiff")
      .click("@secondRunToDiff")
      .assert.not.cssClassPresent("@diffSelectedRunsBtn", "v-btn--disabled")
      .click("@diffSelectedRunsBtn")
      .assert.urlContains("/reports")
      .assert.urlContains("run=")
      .assert.urlContains("newcheck=");

    return this;
  }
};

module.exports = {
  url: function() { 
    return this.api.launchUrl + '/e2e/runs'; 
  },
  commands: [ commands ],
  elements: {
    page: ".v-data-table",
    tableRows: "tbody tr",
    searchInput: ".v-toolbar__content input[type='text']",
    progressBar: ".v-data-table__progress",
    name: "a.name",
    showDescriptionBtn: "button.description",
    showHistoryBtn: "a.show-history",
    showStatisticsBtn: "a.show-statistics",
    showCheckCommandBtn: "button.show-check-command",
    openDetectionStatus: "a.detection-status-count",
    descriptionMenu:
      ".menuable__content__active.run-description-menu .v-card__text",
    removeRunCheckbox: "tbody td:nth-child(1) .v-simple-checkbox",
    deleteSelectedRunsBtn: ".delete-run-btn",
    diffSelectedRunsBtn: ".diff-runs-btn",
    firstRunToDiff:
      "tbody tr:nth-child(1) td:last-child .v-input--checkbox:nth-child(1)",
    secondRunToDiff:
      "tbody tr:nth-child(2) td:last-child .v-input--checkbox:nth-child(2)"
  },
  sections: {
    checkCommandDialog: {
      selector: ".v-dialog__content--active .check-command",
      elements: {
        content: ".container",
        closeBtn: ".v-card__title button"
      }
    },
    removeRunDialog: {
      selector: ".v-dialog__content--active .delete-run-dialog",
      elements: {
        content: ".container",
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn",
        closeBtn: ".v-card__title button"
      }
    }
  }
}
