const commands = {
  backToRunsPage() {
    this.api.back();

    return this
      .pause(500) // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");
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
};

module.exports = {
  url: function() { 
    return this.api.launchUrl + '/e2e/runs'; 
  },
  commands: [ commands ],
  elements: {
    page: ".v-data-table",
    tableRows: "tbody tr",
    progressBar: ".v-data-table__progress",
    name: "a.name",
    showDescriptionBtn: "button.description",
    showHistoryBtn: "a.show-history",
    showStatisticsBtn: "a.show-statistics",
    showCheckCommandBtn: "button.show-analysis-info",
    openDetectionStatus: "a.detection-status-count",
    descriptionMenu:
      ".menuable__content__active.run-description-menu .v-card__text",
    deleteSelectedRunsBtn: ".delete-run-btn",
    diffSelectedRunsBtn: ".diff-runs-btn",
    expandBtn: "button.v-data-table__expand-icon",
  },
  sections: {
    table: {
      selector: "tbody",
      elements: {
        remove: "tr td:nth-child(1) .v-simple-checkbox",
        baseline: "tr td:last-child .v-input--checkbox:nth-child(1)",
        compareTo: "tr td:last-child .v-input--checkbox:nth-child(2)"
      }
    },
    runFilterToolbar: {
      selector: ".run-filter-toolbar",
      elements: {
        runName: ".v-input.run-name input[type='text']",
        runTag: ".v-input.run-tag input[type='text']",
        storedAfter: ".stored-after",
        storedBefore: ".stored-before",
      }
    },
    checkCommandDialog: {
      selector: ".v-dialog__content--active .analysis-info",
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
    },
    expanded: {
      selector: ".v-data-table__expanded__content",
      elements: {
        items: ".v-list-item",
        loadMoreBtn: ".v-btn.load-more-btn"
      },
      sections: {
        timeline: {
          selector: ".v-timeline",
          elements: {
            date: ".date",
            showStatisticsBtn: "a.show-statistics",
            showCheckCommandBtn: "button.show-analysis-info",
            historyEvent: ".v-timeline-item.run-history",
            baseline: ".compare-events .v-input--checkbox:nth-child(1)",
            compareTo: ".compare-events .v-input--checkbox:nth-child(2)"
          }
        }
      }
    }
  }
}
