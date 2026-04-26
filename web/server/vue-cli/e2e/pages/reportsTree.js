// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// Page object for the new view-mode toggle (Report List / File Tree)
// and the file-tree container in web/server/vue-cli/src/views/Reports.vue.

const commands = {
  waitForProgressBarNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@progressBar");
    });
    return this;
  },

  switchToTreeView() {
    this
      .click("@treeViewBtn")
      .pause(500)
      .waitForElementNotPresent("@progressBar");
    this.expect.element("@treeViewContainer").to.be.visible.before(5000);
    return this;
  },

  switchToTableView() {
    this
      .click("@tableViewBtn")
      .pause(500)
      .waitForElementNotPresent("@progressBar");
    this.expect.element("@dataTable").to.be.visible.before(5000);
    return this;
  }
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
    progressBar: ".v-data-table__progress",

    // View-mode toggle (Vuetify v-btn-toggle with two v-btn entries).
    viewModeToggle: ".v-btn-toggle",
    tableViewBtn: ".v-btn-toggle .v-btn:nth-child(1)",
    treeViewBtn: ".v-btn-toggle .v-btn:nth-child(2)",

    dataTable: ".v-data-table",

    treeViewContainer: ".tree-view-container",
    treeHeader: ".tree-view-container .tree-header",
    treeHeaderName: ".tree-view-container .tree-header-name",
    treeHeaderCell: ".tree-view-container .tree-header-cell",
    treeRow: ".tree-view-container .tree-row",
    treeItemLabel:
      ".tree-view-container .tree-item-label.clickable",
    treeStatCell: ".tree-view-container .tree-stat-cell"
  },
  sections: {
    // Re-declare the file-path filter section so this spec can assert that
    // clicking a tree item populates it.
    filePathFilter: {
      selector: "#filepath",
      elements: {
        expansionBtn: ".expansion-btn",
        clearBtn: ".clear-btn",
        selectedItems: ".selected-item"
      }
    }
  }
};
