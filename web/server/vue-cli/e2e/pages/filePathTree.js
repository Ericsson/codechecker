// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// Page object for the file-path filter's tree-based menu content
// (FilePathFilter.vue). Shares the same overall layout as the report page
// (login is performed via browser.page.login() in the spec), but only
// exposes the tree-specific elements/sections.

const commands = {
  waitForProgressBarNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@progressBar");
    });
    return this;
  },

  openFilePathFilterMenu() {
    const filterSection = this.section.filePathFilter;
    filterSection.click("@expansionBtn");
    filterSection.click("@settings");
    this.expect.section("@filePathTreeMenu").to.be.visible.before(5000);
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
    progressBar: ".v-data-table__progress"
  },
  sections: {
    filePathFilter: {
      selector: "#filepath",
      elements: {
        expansionBtn: ".expansion-btn",
        settings: ".settings-btn",
        clearBtn: ".clear-btn",
        selectedItems: ".selected-item"
      }
    },
    filePathTreeMenu: {
      // The settings-menu popup that hosts the file-path tree.
      selector: ".settings-menu.menuable__content__active",
      elements: {
        searchInput: "header input[type='text']",
        anywhereSwitch: ".v-input--switch",
        tree: ".file-path-tree",
        treeNode: ".file-path-tree .v-treeview-node",
        treeRootNode: ".file-path-tree > .v-treeview-node",
        treeNodeRoot: ".file-path-tree .v-treeview-node__root",
        treeItemLabel: ".file-path-tree .tree-item-label",
        treeCheckbox: ".file-path-tree .v-treeview-node__checkbox",
        applyBtn: ".apply-btn",
        clearAllBtn: ".clear-all-btn"
      }
    }
  }
};
