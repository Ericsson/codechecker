module.exports = {
  before(browser) {
    const login = browser.page.login();

    const runHistoryPage = browser.page.history();

    login
      .navigate(runHistoryPage.url())
      .loginAsRoot();

    browser.expect.url().to.equal(runHistoryPage.url()).before(5000);

    runHistoryPage.waitForElementVisible("@page", 10000);
  },

  after(browser) {
    browser.end();
  },

  "test run history page" (browser) {
    const runHistoryPage = browser.page.history();
    const runName = "simple";
    const tag = "v0.0.2";
    const description = "This is my updated run.";
    const checkCommand = "CodeChecker.py analyze";

    runHistoryPage
      .perform(async () => {
        runHistoryPage.clearAndSetValue("@searchRunNameInput", runName);

        await runHistoryPage.waitForProgressBarNotPresent();

        runHistoryPage
          .getTableRows("@tableRows" , (history) => {
            browser.assert.ok(history.length === 2);
            browser.assert.ok(history[0][0].includes(runName));
            browser.assert.ok(history[1][0].includes(runName));
          })
          .assert.urlContains(`run=${runName}`)
      })
      .perform(async () => {
        runHistoryPage
          .diffFirstTwoRunHistoryItems()
          .assert.urlContains("/reports")
          .assert.urlContains(`run-tag=${tag}`)
          .assert.urlContains("first-detection-date=")
          .assert.urlContains("fix-date=")
          .back();

        await runHistoryPage.waitForProgressBarNotPresent();
      })
      .perform(async () => {
        runHistoryPage.clearAndSetValue("@searchRunTagInput", tag);

        await runHistoryPage.waitForProgressBarNotPresent();

        runHistoryPage
          .getTableRows("@tableRows" , (history) => {
            browser.assert.ok(history.length === 1);
            browser.assert.ok(history[0][4].includes(tag));
          })
          .assert.urlContains(`run=${runName}`)
          .assert.urlContains(`run-tag=${tag}`)
      })
      .perform(async () => {
        runHistoryPage
          .click("@showStatisticsBtn")
          .assert.urlContains("/statistics")
          .assert.urlContains(`run=${runName}`)
          .assert.urlContains("is-unique=on")
          .assert.urlContains("detection-status=New")
          .assert.urlContains("detection-status=Reopened")
          .assert.urlContains("detection-status=Unresolved")
          .back();

        await runHistoryPage.waitForProgressBarNotPresent();
      })
      .perform(() => {
        runHistoryPage
          .click("@showDescriptionBtn")
          .waitForElementVisible("@descriptionMenu")
          .assert.containsText("@descriptionMenu", description)
          .click("@showDescriptionBtn")
          .waitForElementNotPresent("@descriptionMenu");
      })
      .perform(async () => {
        await runHistoryPage.click("@showCheckCommandBtn");

        runHistoryPage.expect.section("@checkCommandDialog").to.be.visible;

        const section = runHistoryPage.section.checkCommandDialog;

        section.assert.containsText("@content", checkCommand);
        await section.click("@closeBtn");

        runHistoryPage.expect.section("@checkCommandDialog")
          .to.not.be.present.before(5000);
      });
  }
}
