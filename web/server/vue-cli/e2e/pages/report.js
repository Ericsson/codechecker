const commands = {
  waitForProgressBarNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@progressBar");
    });
    return this;
  },

  sortReports(column, isSorted) {
    return this
      .click(`th:nth-child(${column})`)
      .waitForProgressBarNotPresent()
      .getTableRows("@tableRows", (data) => {
        this.api.assert.ok(isSorted(data), "reports are not sorted");
      });
  }
};

const filterCommands = {
  openFilterSettings() {
    this.click("@settings");

    const reportPage = this.api.page.report();
    reportPage.expect.section("@settingsMenu").to.be.visible.before(5000);

    return this;
  },

  selectedItemClick(index) {
    return this.click({ selector: "@selectedItems", index: index});
  }
};

const menuCommands = {
  applyFilter() {
    return this.click("@applyBtn");
  },

  search(item) {
    return this
      .clearAndSetValue("@searchInput", item, this)
      .pause(500)
      .waitForElementNotPresent("@progressBar");
  },

  toggleMenuItem(index) {
    return this.click({ selector: "@item", index: index });
  }
};

const createOptionFilterSection = (selector) => {
  return {
    selector,
    elements: {
      expansionBtn: ".expansion-btn",
      settings: ".settings-btn",
      clearBtn: ".clear-btn",
      selectedItems: ".selected-item"
    },
    commands: [ filterCommands ]
  };
};

const createRunFilterSection = (selector) => {
  return {
    selector,
    elements: {
      expansionBtn: ".expansion-btn",
      settings: ".settings-btn",
      clearBtn: ".clear-btn",
      selectedItems: ".selected-item"
    },
    commands: [ filterCommands ]
  };
};

const createDateRageFilterSection = (selector) => {
  return {
    selector,
    elements: {
      expansionBtn: ".expansion-btn",
      settings: ".settings-btn",
      clearBtn: ".clear-btn",
      selectedItems: ".selected-item",
      from: ".row > div:first-child .v-input",
      to: ".row > div:last-child .v-input"
    }
  };
};

const createOpenReportsDateFilterSection = (selector) => {
  return {
    selector,
    elements: {
      expansionBtn: ".expansion-btn",
      clearBtn: ".clear-btn",
      input: ".v-input",
    }
  };
};


const settingsMenuElements = {
  searchInput: "header input[type='text']",
  progressBar: ".v-progress-linear",
  regexItem: ".v-item-group > .v-list-item",
  item: ".v-item-group:last-child > .v-list-item",
  applyBtn: ".apply-btn",
  cancelBtn: ".cancel-btn"
};

module.exports = {
  url: function() {
    return this.api.launchUrl + "/e2e/reports?review-status=Unreviewed&"
      + "review-status=Confirmed%20bug&detection-status=New&"
      + "detection-status=Reopened&detection-status=Unresolved";
  },
  commands: [ commands ],
  elements: {
    page: ".v-data-table",
    tableRows: "tbody tr",
    progressBar: ".v-data-table__progress",
    clearAllFilterBtn: "#clear-all-filter-btn",
    uniqueReports: ".unique-filter .v-input--checkbox",
    expandBtn: "button.v-data-table__expand-icon",
  },
  sections: {
    baselineRunFilter: createRunFilterSection("#run"),
    baselineOpenReportsDateFilter:
    createOpenReportsDateFilterSection("#open-reports-date"),
    compareToFilters: {
      selector: "#compare-to-filters",
      elements: {
        expansionBtn: ".v-expansion-panel-header__icon",
        active: ".v-expansion-panel--active"
      },
      sections: {
        compareToRunFilter: createRunFilterSection("#newcheck"),
        compareToOpenReportsDateFilter:
        createOpenReportsDateFilterSection("#compared-to-open-reports-date"),
        compareToDiffTypeFilter: createOptionFilterSection("#diff-type"),
      }
    },
    filePathFilter: createOptionFilterSection("#filepath"),
    checkerNameFilter: createOptionFilterSection("#checker-name"),
    checkerMessageFilter: createOptionFilterSection("#checker-msg"),
    severityFilter: createOptionFilterSection("#severity"),
    reviewStatusFilter: createOptionFilterSection("#review-status"),
    detectionStatusFilter: createOptionFilterSection("#detection-status"),
    analyzerNameFilter: createOptionFilterSection("#analyzer-name"),
    bugPathLengthFilter: {
      selector: "#bug-path-length-filter",
      elements: {
        expansionBtn: ".expansion-btn",
        min: "#min-bug-path-length",
        max: "#max-bug-path-length",
        clearBtn: ".clear-btn",
      }
    },
    reportHashFilter: {
      selector: "#report-hash-filter",
      elements: {
        expansionBtn: ".expansion-btn",
        reportHash: "#report-hash",
        clearBtn: ".clear-btn"
      }
    },
    sourceComponentFilter: {
      selector: "#source-component",
      elements: {
        expansionBtn: ".expansion-btn",
        manageBtn: ".manage-components-btn",
        settings: ".settings-btn",
        clearBtn: ".clear-btn",
        selectedItems: ".selected-item"
      },
      commands: [ filterCommands ]
    },
    sourceComponentDialog: {
      selector: ".manage-source-component-dialog.v-dialog--active",
      elements: {
        newComponentBtn: ".new-component-btn",
        tableRows: ".v-data-table tbody tr",
        emptyTable: ".v-data-table tbody .v-data-table__empty-wrapper",
        editBtn: ".edit-btn",
        removeBtn: ".remove-btn",
        closeBtn: ".close-btn"
      }
    },
    newSourceComponentDialog: {
      selector: ".edit-source-component-dialog.v-dialog--active",
      elements: {
        name: ".component-name input[type='text']",
        value: ".component-value textarea",
        description: ".component-description textarea",
        saveBtn: ".save-btn",
        cancelBtn: ".cancel-btn",
      }
    },
    removeSourceComponentDialog: {
      selector: ".remove-source-component-dialog.v-dialog--active",
      elements: {
        confirmBtn: ".remove-btn",
        cancelBtn: ".cancel-btn",
      }
    },
    dateFilters: {
      selector: "#date-filters",
      elements: {
        expansionBtn: ".v-expansion-panel-header__icon",
        active: ".v-expansion-panel--active"
      },
      sections: {
        detectionDateFilter:
          createDateRageFilterSection("#detection-date-filter"),
        fixDateFilter: createDateRageFilterSection("#fix-date-filter")
      }
    },
    openReportsDateDialog: {
      selector: ".v-dialog--active",
      elements: {
        date: ".v-date-picker-table td button",
        ok: ".ok-btn"
      }
    },
    fromDateDialog: {
      selector: ".v-dialog--active",
      elements: {
        date: ".v-date-picker-table td button",
        ok: ".ok-btn"
      }
    },
    toDateDialog: {
      selector: ".v-dialog--active",
      elements: {
        date: ".v-date-picker-table td button",
        ok: ".ok-btn"
      }
    },
    runSettingsMenu: {
      selector: ".settings-menu.menuable__content__active",
      elements: {
        ...settingsMenuElements,
        selectTagButton: ".v-btn"
      },
      commands: [ menuCommands ]
    },
    tagSettingsMenu: {
      selector: ".select-tag-menu.menuable__content__active",
      elements: {
        ...settingsMenuElements
      },
      commands: [ menuCommands ]
    },
    settingsMenu: {
      selector: ".settings-menu.menuable__content__active",
      elements: settingsMenuElements,
      commands: [ menuCommands ]
    },
    expanded: {
      selector: ".v-data-table__expanded__content",
      elements: {
        items: ".v-list-item"
      }
    }
  }
}
