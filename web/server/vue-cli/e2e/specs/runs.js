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

  "test run list page" (browser) {
    const runs = browser.page.runs();
    const runName = "remove";
    const tag = "v0.0.1-deprecated";
    const description = "This can can be removed.";
    const checkCommand = "CodeChecker.py analyze";

    runs
      .perform(() => {
        runs.sortRuns(2, (data) => {
          return data.every((e, ind, a) => !ind || a[ind - 1][1] <= e[1]);
        });
      })
      .perform(() => {
        runs.sortRuns(3, (data) => {
          return data.every((e, ind, a) =>
            !ind || parseInt(a[ind - 1][2]) <= parseInt(e[2]));
        });
      })
      .perform(() => {
        runs.sortRuns(3, (data) => {
          return data.every((e, ind, a) =>
            !ind || parseInt(a[ind - 1][2]) >= parseInt(e[2]));
        });
      })
      .perform(() => {
        runs
          .diffFirstTwoRuns()
          .backToRunsPage();
      })
      .perform(() => {
        runs.filterRuns(runName, (runs) => {
          browser.assert.ok(runs.length === 1);
          browser.assert.ok(runs[0][1].includes(tag));
        });
      })
      .perform(() => {
        runs
          .openRun(runName)
          .backToRunsPage();
      })
      .perform(() => {
        runs
          .openRunHistory(runName)
          .backToRunsPage();
      })
      .perform(() => {
        runs
          .openStatistics(runName)
          .backToRunsPage();
      })
      .perform(() => {
        runs
          .openDetectionStatus(runName)
          .backToRunsPage();
      })
      .perform(() => {
        runs
          .showDescription()
          .assert.containsText("@descriptionMenu", description)
          .closeDescription()
      })
      .perform(() => {
        runs
          .showCheckCommand()
          .perform(() => {
            const section = runs.section.checkCommandDialog;

            section.assert.containsText("@content", checkCommand);

            runs.closeCheckCommand();
          })
      })
      .perform(() => {
        runs
          .removeFirstRun()
          .pause(500) // Wait some time to make sure progressbar appeared.
          .waitForElementNotPresent("@progressBar")
          .getTableRows("@tableRows", (runs) => {
            browser.assert.ok(runs.length === 1);
            browser.assert.ok(runs[0][0].includes("No data available"));
          });
      });
  }
}
