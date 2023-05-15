module.exports = {
  before(browser) {
    browser.resizeWindow(1800, 1000);

    const login = browser.page.login();

    const reviewStatusRulePage = browser.page.reviewStatusRule();

    login
      .navigate(reviewStatusRulePage.url())
      .loginAsRoot();

    browser.expect.url().to.contain(reviewStatusRulePage.url()).before(5000);

    reviewStatusRulePage
      .waitForElementVisible("@page", 10000)
      .waitForProgressBarNotPresent();
  },

  after(browser) {
    browser.perform(() => {
      browser.end();
    });
  },

  "add new review status rule" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();
    const dialog = reviewStatusRulePage.section.editReviewStatusRuleDialog;
    const selectReviewStatusMenu =
      reviewStatusRulePage.section.selectReviewStatusMenu;

    reviewStatusRulePage.click("@newReviewStatusRuleBtn");

    reviewStatusRulePage.expect.section(dialog).to.be.visible.before(5000);

    dialog.clearAndSetValue("@reportHash", "INVALID1", dialog);

    dialog.click("@selectReviewStatus");
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.be.present.before(5000);
    selectReviewStatusMenu.click({ selector: "@item", index: 2 });
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.not.be.present.before(5000);

    dialog.clearAndSetValue("@message", "Test", dialog);

    dialog.click("@confirmBtn");

    reviewStatusRulePage.expect.section(dialog).to.not.be.present.before(5000);

    reviewStatusRulePage.waitForProgressBarNotPresent();
  },

  "filter review status rules" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();
    const filters = reviewStatusRulePage.section.filters;
    const selectReviewStatusMenu =
      reviewStatusRulePage.section.selectReviewStatusMenu;

    const reportHash = "INVALID";
    const author = "root";

    filters.clearAndSetValue("@reportHash", reportHash);
    filters.clearAndSetValue("@author", author);

    filters.click("@selectReviewStatus");
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.be.present.before(5000);
    selectReviewStatusMenu.click({ selector: "@item", index: 2 });
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.not.be.present.before(5000);

    filters.click("@noAssociatedReports");

    reviewStatusRulePage.waitForProgressBarNotPresent();

    reviewStatusRulePage
      .assert.urlContains(`report-hash=${reportHash}`)
      .assert.urlContains(`author=${author}`)
      .assert.urlContains("no-associated-reports=on")
      .assert.urlContains("review-status=False%20positive")
  },

  "edit review status rule" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();
    const dialog = reviewStatusRulePage.section.editReviewStatusRuleDialog;

    reviewStatusRulePage.click("@editReviewStatusRuleBtn");

    reviewStatusRulePage.expect.section(dialog).to.be.visible.before(5000);

    dialog.clearAndSetValue("@message", "Updated message", dialog);
    dialog.click("@confirmBtn");

    reviewStatusRulePage.expect.section(dialog).to.not.be.present.before(5000);

    reviewStatusRulePage.waitForProgressBarNotPresent();
  },

  "remove a review status rule" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();
    const dialog = reviewStatusRulePage.section.removeReviewStatusRuleDialog;

    reviewStatusRulePage.click("@removeReviewStatusRuleBtn");

    reviewStatusRulePage.expect.section(dialog).to.be.visible.before(5000);

    reviewStatusRulePage.section.removeReviewStatusRuleDialog.click("@confirmBtn");

    reviewStatusRulePage.expect.section(dialog).to.not.be.present.before(5000);

    reviewStatusRulePage.waitForProgressBarNotPresent();

    // There is no more item review status rule based on the filters
    reviewStatusRulePage.waitForElementNotPresent(
      "@removeReviewStatusRuleBtn");
  },

  "clear all review status filters" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();

    reviewStatusRulePage.click("@clearAllFiltersBtn");

    reviewStatusRulePage.waitForProgressBarNotPresent();

    reviewStatusRulePage.waitForElementVisible(
      "@removeReviewStatusRuleBtn");
  },
  
  "remove all filtered review status rules" (browser) {
    const reviewStatusRulePage = browser.page.reviewStatusRule();
    const editDialog = reviewStatusRulePage.section.editReviewStatusRuleDialog;
    const removeDialog =
      reviewStatusRulePage.section.removeFilteredRulesDialog;
    const filters = reviewStatusRulePage.section.filters;
    const selectReviewStatusMenu =
      reviewStatusRulePage.section.selectReviewStatusMenu;

    reviewStatusRulePage.click("@newReviewStatusRuleBtn");

    reviewStatusRulePage.expect.section(editDialog).to.be.visible.before(5000);
    
    const reportHash = "INVALID1";
    editDialog.clearAndSetValue("@reportHash", reportHash, editDialog);

    editDialog.click("@selectReviewStatus");
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.be.present.before(5000);
    selectReviewStatusMenu.click({ selector: "@item", index: 2 });
    reviewStatusRulePage.expect.section(selectReviewStatusMenu)
      .to.not.be.present.before(5000);

    editDialog.click("@confirmBtn");

    reviewStatusRulePage.expect.section(editDialog)
      .to.not.be.present.before(5000);

    reviewStatusRulePage.waitForProgressBarNotPresent();

    // Filter the rules to show only the rule above.
    filters.clearAndSetValue("@reportHash", reportHash);
    reviewStatusRulePage.waitForProgressBarNotPresent();

    // Remove all filtered rules.
    reviewStatusRulePage.click("@removeFilteredRulesBtn");
    reviewStatusRulePage.waitForProgressBarNotPresent();

    reviewStatusRulePage.expect.section(removeDialog)
      .to.be.visible.before(5000);
    removeDialog.click("@confirmBtn");
    reviewStatusRulePage.expect.section(removeDialog)
      .to.not.be.present.before(5000);

    reviewStatusRulePage.waitForProgressBarNotPresent();

    // There is no more review status rule based on the filters.
    reviewStatusRulePage.waitForElementNotPresent(
      "@removeReviewStatusRuleBtn");

    reviewStatusRulePage.click("@clearAllFiltersBtn");

    reviewStatusRulePage.waitForProgressBarNotPresent();

    reviewStatusRulePage.waitForElementVisible(
      "@removeReviewStatusRuleBtn");
  },
}
