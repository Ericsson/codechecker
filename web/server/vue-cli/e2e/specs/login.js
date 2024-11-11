module.exports = {
  before (browser) {
    this.loginPage = `${browser.launchUrl}/login`;
  },

  "show login page when not authenticated" (browser) {
    // Visiting default page.
    browser
      .url(browser.launchUrl)
      .waitForElementVisible('body')
      .assert.urlEquals(`${this.loginPage}?return_to=%2F`);

    // Visiting product page.
    browser
      .url(`${browser.launchUrl}/`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${this.loginPage}?return_to=%2F`);

    // Visiting run page.
    browser
      .url(`${browser.launchUrl}/e2e/runs`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${this.loginPage}?return_to=%2Fe2e%2Fruns`);

    // Visiting statistics page.
    browser
      .url(`${browser.launchUrl}/e2e/statistics`)
      .waitForElementVisible('body')
      .assert.urlEquals(
        `${this.loginPage}?return_to=%2Fe2e%2Fstatistics%2Foverview`);

    // Visiting old statistics page url.
    browser
      .url(`${browser.launchUrl}/e2e/#tab=statistics`)
      .waitForElementVisible('body')
      .assert.urlEquals(
        `${this.loginPage}?return_to=%2Fe2e%2Fstatistics%2Foverview`);

    // Visiting reports page.
    browser
      .url(`${browser.launchUrl}/e2e/reports`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${this.loginPage}?return_to=%2Fe2e%2Freports`);

    // Visiting report detail page.
    browser
      .url(`${browser.launchUrl}/e2e/report-detail`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${this.loginPage}?return_to=%2Fe2e%2Freport-detail`);

    browser.end();
  },

  "show pages which does not require authentication" (browser) {
    // Visiting the useguide page.
    browser
      .url(`${browser.launchUrl}/userguide`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${browser.launchUrl}/userguide`);

    // Visiting the new features page.
    browser
      .url(`${browser.launchUrl}/new-features`)
      .waitForElementVisible('body')
      .assert.urlEquals(`${browser.launchUrl}/new-features`);

    browser.end();
  },

  "login with invalid credentials" (browser) {
    const login = browser.page.login();

    login
      .navigate()
      .login("", "")
      .assert.containsText("@userNameErrorMessages", "required")
      .assert.containsText("@passwordErrorMessages", "required")
      .login("dummy", "NoSuchUser")
      .assert.containsText("@alertError", "Failed to log in!")
      .end()
  },

  "login as root user" (browser) {
    const login = browser.page.login();

    login
      .navigate()
      .loginAsRoot()
      .assert.urlEquals(`${browser.launchUrl}/`)
      .end();
  }
};
