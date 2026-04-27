// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// E2E tests for the new file-tree view mode and the severity / review-status
// header columns added to web/server/vue-cli/src/views/Reports.vue.

module.exports = {
  before(browser) {
    browser.resizeWindow(1600, 1000);

    const login = browser.page.login();
    const treePage = browser.page.reportsTree();

    login
      .navigate(treePage.url())
      .loginAsRoot();

    browser.assert.urlContains("/e2e/reports");

    treePage
      .waitForElementVisible("@page", 10000)
      .waitForProgressBarNotPresent();

    // Make sure the file-path filter section is expanded so that we can
    // inspect the chips later.
    const reportPage = browser.page.report();
    reportPage.section.filePathFilter.click("@expansionBtn");
  },

  after(browser) {
    browser.perform(() => {
      browser.end();
    });
  },

  "default view is the data table" (browser) {
    const page = browser.page.reportsTree();
    page.expect.element("@viewModeToggle").to.be.visible.before(5000);
    page.expect.element("@dataTable").to.be.visible.before(5000);
    page.expect.element("@treeViewContainer").to.not.be.present.before(5000);
  },

  "switching to tree view shows the tree container" (browser) {
    const page = browser.page.reportsTree();
    page.switchToTreeView();

    page.expect.element("@treeViewContainer").to.be.visible.before(5000);
    page.expect.element("@dataTable").to.not.be.present.before(5000);
  },

  "tree header shows severity and review-status columns" (browser) {
    const page = browser.page.reportsTree();

    page.expect.element("@treeHeader").to.be.visible.before(5000);
    page.expect.element("@treeHeaderName").text.to.contain("Name");

    // The header has 1 "All" + 5 severities + 4 review statuses = 10
    // tree-header-cell elements.
    browser.elements("css selector", ".tree-header-cell", function (result) {
      browser.assert.ok(
        Array.isArray(result.value) && result.value.length === 10,
        "tree header should contain 10 stat columns "
          + "(All + 5 severities + 4 review statuses), got "
          + (result.value ? result.value.length : "none")
      );
    });
  },

  "tree rows render stat cells" (browser) {
    const page = browser.page.reportsTree();

    page.expect.element("@treeRow").to.be.present.before(5000);
    browser.elements("css selector",
      ".tree-view-container .tree-row", function (result) {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length > 0,
          "the tree should render at least one row"
        );
      });
  },

  "clicking a tree item populates the file path filter" (browser) {
    const page = browser.page.reportsTree();

    page.expect.element("@treeItemLabel").to.be.present.before(5000);

    page
      .click({ selector: "@treeItemLabel", index: 0 })
      .pause(500)
      .waitForElementNotPresent("@progressBar");

    page.section.filePathFilter.api.elements("@selectedItems",
      ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length >= 1,
          "clicking a tree node must add at least one file-path filter chip"
        );
      });
  },

  "switching back to table view clears the file path filter" (browser) {
    const page = browser.page.reportsTree();

    page.switchToTableView();

    // Both view-toggle buttons in Reports.vue invoke
    // setReportFilter({ filepath: null }) on click, so the chip set
    // populated in the previous test must now be empty.
    page.section.filePathFilter.api.elements("@selectedItems",
      ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length === 0,
          "switching back to the table view should clear file-path filter"
        );
      });

    page.expect.element("@dataTable").to.be.visible.before(5000);
  }
};
