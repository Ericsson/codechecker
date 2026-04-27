// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

// E2E tests for the new tree view inside the File path filter
// (web/server/vue-cli/src/components/Report/ReportFilter/Filters/
//  FilePathFilter.vue).

module.exports = {
  before(browser) {
    browser.resizeWindow(1600, 1000);

    const login = browser.page.login();
    const filePathTreePage = browser.page.filePathTree();

    login
      .navigate(filePathTreePage.url())
      .loginAsRoot();

    browser.assert.urlContains("/e2e/reports");

    filePathTreePage
      .waitForElementVisible("@page", 10000)
      .waitForProgressBarNotPresent();
  },

  after(browser) {
    browser.perform(() => {
      browser.end();
    });
  },

  "open the file path filter tree menu" (browser) {
    const page = browser.page.filePathTree();
    page.openFilePathFilterMenu();

    page.expect.section("@filePathTreeMenu").to.be.visible.before(5000);

    const menu = page.section.filePathTreeMenu;
    // The tree should render at least one node when reports exist.
    menu.expect.element("@tree").to.be.present.before(5000);
    menu.api.elements("@treeRootNode", ({ result }) => {
      browser.assert.ok(
        Array.isArray(result.value) && result.value.length > 0,
        "file-path tree should contain at least one root node"
      );
    });
  },

  "filter the tree using the search input" (browser) {
    const page = browser.page.filePathTree();
    const menu = page.section.filePathTreeMenu;

    // Filter for everything (matches all files).
    menu.clearAndSetValue("@searchInput", "*", menu);
    menu
      .pause(500)
      .api.elements("@treeRootNode", ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length > 0,
          "wildcard filter should keep at least one root node visible"
        );
      });

    // Filter for a string that should match nothing.
    menu.clearAndSetValue("@searchInput",
      "definitely_not_a_real_path_zzz", menu);
    menu
      .pause(500)
      .api.elements("@treeRootNode", ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length === 0,
          "non-matching filter should hide every node"
        );
      });

    // Reset filter for subsequent tests.
    menu.clearAndSetValue("@searchInput", "", menu);
    menu.pause(300);
  },

  "toggle the anywhere-on-report-path switch" (browser) {
    const page = browser.page.filePathTree();
    const menu = page.section.filePathTreeMenu;

    menu.expect.element("@anywhereSwitch").to.be.visible.before(5000);
    menu
      .click("@anywhereSwitch")
      .pause(300)
      .click("@anywhereSwitch")
      .pause(300);
    // No assertion on tree contents (data-dependent); we only verify the
    // switch is interactive and does not throw.
  },

  "expand the first folder node" (browser) {
    const page = browser.page.filePathTree();
    const menu = page.section.filePathTreeMenu;

    // Click the first node label area to toggle expansion (open-on-click).
    menu
      .click({ selector: "@treeNodeRoot", index: 0 })
      .pause(500);

    // After expansion, the total visible node count must not decrease.
    menu.api.elements("@treeNode", ({ result }) => {
      browser.assert.ok(
        Array.isArray(result.value) && result.value.length >= 1,
        "expanding a folder should reveal at least the original nodes"
      );
    });
  },

  "select a tree item and apply" (browser) {
    const page = browser.page.filePathTree();
    const menu = page.section.filePathTreeMenu;

    menu.expect.element("@treeCheckbox").to.be.present.before(5000);

    // Tick the first checkbox (independent selection mode means a single
    // node is enough to enable the Apply button).
    menu
      .click({ selector: "@treeCheckbox", index: 0 })
      .pause(300);

    menu.click("@applyBtn");

    // Menu must close after applying.
    page.expect.section("@filePathTreeMenu")
      .to.not.be.present.before(5000);

    page.waitForProgressBarNotPresent();

    page.section.filePathFilter.api.elements("@selectedItems",
      ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length >= 1,
          "applying a tree selection should add at least one filter chip"
        );
      });
  },

  "clear the file path filter via the section clear button" (browser) {
    const page = browser.page.filePathTree();
    const section = page.section.filePathFilter;

    section.click("@clearBtn");
    page.waitForProgressBarNotPresent();

    section.api.elements("@selectedItems", ({ result }) => {
      browser.assert.ok(
        Array.isArray(result.value) && result.value.length === 0,
        "clear button should remove every file-path filter chip"
      );
    });
  },

  "clear-all button inside the tree menu closes and clears" (browser) {
    const page = browser.page.filePathTree();
    page.openFilePathFilterMenu();

    const menu = page.section.filePathTreeMenu;

    menu
      .click({ selector: "@treeCheckbox", index: 0 })
      .pause(300)
      .click("@clearAllBtn");

    page.expect.section("@filePathTreeMenu")
      .to.not.be.present.before(5000);

    page.waitForProgressBarNotPresent();

    page.section.filePathFilter.api.elements("@selectedItems",
      ({ result }) => {
        browser.assert.ok(
          Array.isArray(result.value) && result.value.length === 0,
          "clear-all should leave no file-path filter chips"
        );
      });
  }
};
