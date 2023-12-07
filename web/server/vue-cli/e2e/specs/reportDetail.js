module.exports = {
  before(browser) {
    browser.resizeWindow(1600, 1000);

    const login = browser.page.login();

    const reportDetailPage = browser.page.reportDetail();

    login
      .navigate(reportDetailPage.url())
      .loginAsRoot();

    browser.expect.url().to.contain(reportDetailPage.url()).before(5000);

    reportDetailPage
      .waitForElementVisible("@page", 10000)
      .waitForProgressBarNotPresent();
  },

  after(browser) {
    browser.perform(() => {
      browser.end();
    });
  },

  "show documentation" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    reportDetailPage.expect.element('@showDocumentationBtn')
      .to.be.present.before(5000, false);

    reportDetailPage.click('@showDocumentationBtn');

    browser.windowHandles(windowObj => {
      if (windowObj.value.length > 1) {
        browser.switchWindow(windowObj.value[1]);
        browser.closeWindow();
        browser.switchWindow(windowObj.value[0]);
      }
    });
  },

  "show blame information" (browser) {
    const reportDetailPage = browser.page.reportDetail();

    reportDetailPage
      .click("@toggleBlameViewBtn")
      .waitForElementVisible("@blameCommitInfo")
      .click("@toggleBlameViewBtn")
      .waitForElementNotPresent("@blameCommitInfo");
  },

  "change review status without message" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const selectReviewStatusMenu =
      reportDetailPage.section.selectReviewStatusMenu;
    const changeReviewStatusMessageDialog =
      reportDetailPage.section.changeReviewStatusMessageDialog;

    // Open the selector.
    reportDetailPage.click("@selectReviewStatus");

    reportDetailPage.expect.section(selectReviewStatusMenu)
      .to.be.visible.before(5000);

    // Select an item.
    selectReviewStatusMenu.click({ selector: "@item", index: 1 });

    reportDetailPage.expect.section(changeReviewStatusMessageDialog)
      .to.be.visible.before(5000);

    reportDetailPage.expect.element("@overlay").to.be.visible.before(5000);

    // Clear the message.
    changeReviewStatusMessageDialog
      .clearAndSetValue("@message", "", changeReviewStatusMessageDialog)
      .click("@save");

    reportDetailPage.expect.element("@reviewStatusMessage")
      .to.be.not.present.before(5000);
  },

  "change review status with a message" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const selectReviewStatusMenu =
      reportDetailPage.section.selectReviewStatusMenu;
    const changeReviewStatusMessageDialog =
      reportDetailPage.section.changeReviewStatusMessageDialog;
    const reviewStatusMessageMenu =
      reportDetailPage.section.reviewStatusMessageMenu;

    // Open the selector.
    reportDetailPage.click("@selectReviewStatus");

    reportDetailPage.expect.section(selectReviewStatusMenu)
      .to.be.visible.before(5000);

    // Select an item.
    selectReviewStatusMenu.click({ selector: "@item", index: 2 });

    reportDetailPage.expect.section(changeReviewStatusMessageDialog)
      .to.be.visible.before(5000);

    reportDetailPage.expect.element("@overlay").to.be.visible.before(5000);

    // Set the message and save.
    const message = "Test";
    changeReviewStatusMessageDialog
      .clearAndSetValue("@message", message, changeReviewStatusMessageDialog)
      .click("@save");

    // Check that message is updated properly.
    reportDetailPage.click("@reviewStatusMessage");

    reportDetailPage.expect.section(reviewStatusMessageMenu)
      .to.be.visible.before(5000);

    reviewStatusMessageMenu.expect.element("@message").text.to.equal(message);

    reportDetailPage.click("@page");
    reportDetailPage.expect.section(reviewStatusMessageMenu)
      .to.be.not.present.before(5000);
    reportDetailPage.expect.element("@overlay").to.not.be.present.before(5000);
  },

  async "manage comments" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const commentsPane = reportDetailPage.section.commentsPane;
    const userCommentSection = commentsPane.section.userComment;
    const systemCommentSection = commentsPane.section.systemComment;
    const editCommentDialog = reportDetailPage.section.editCommentDialog;
    const removeCommentDialog = reportDetailPage.section.removeCommentDialog;

    const message = `e2e ${+new Date}`;
    const newMessage = `${message} renamed`;

    reportDetailPage.click("@commentsBtn");

    reportDetailPage.expect.section(commentsPane)
      .to.be.visible.before(5000);

    // Add new comment.
    commentsPane.clearAndSetValue("@message", message, commentsPane);
    commentsPane.click("@addBtn");

    commentsPane.waitForOverlayNotPresent();

    commentsPane.waitForElementVisible(userCommentSection);

    userCommentSection.expect.element("@message").text.to.equal(message);

    // Edit comment.
    userCommentSection.click("@editBtn");
    reportDetailPage.expect.section(editCommentDialog)
      .to.be.visible.before(5000);

    reportDetailPage.expect.element("@overlay").to.be.visible.before(5000);

    editCommentDialog
      .clearAndSetValue("@message", newMessage, editCommentDialog);

    editCommentDialog.click("@saveBtn");

    commentsPane.waitForOverlayNotPresent();

    userCommentSection.expect.element("@message").text.to.equal(newMessage);
    systemCommentSection.expect.element("@message").text.to.contain(
      `changed comment message from ${message} to ${newMessage}`)

    // Remove comment.
    userCommentSection.click("@removeBtn");
    reportDetailPage.expect.section(removeCommentDialog)
      .to.be.visible.before(5000);
    reportDetailPage.expect.element("@overlay").to.be.visible.before(5000);

    removeCommentDialog.pause(100).click("@removeBtn");

    reportDetailPage.expect.section(removeCommentDialog)
      .to.be.not.present.before(5000);

    commentsPane.waitForOverlayNotPresent();

    commentsPane.waitForElementNotPresent(userCommentSection);

    // Close comments.
    reportDetailPage.click("@commentsBtn");

    reportDetailPage.expect.section(commentsPane)
      .to.be.not.present.before(5000);
  },

  "found in" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const selectSameReportMenu = reportDetailPage.section.selectSameReportMenu;

    // Open the selector.
    reportDetailPage.click("@selectSameReport");

    reportDetailPage.expect.section(selectSameReportMenu)
      .to.be.visible.before(5000);

    // Select an item.
    selectSameReportMenu.click({ selector: "@item", index: 1 });

    reportDetailPage.expect.section(selectSameReportMenu)
      .to.be.not.present.before(5000);

    // TODO: We need to wait for a couple of seconds to make sure that progress
    // bar appears while we check that it dissapear.
    reportDetailPage.pause(1500, () => {
      reportDetailPage.waitForElementNotPresent("@progressBar");
    });
  },

  async "open bug step" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const bugTree = reportDetailPage.section.bugTree;

    // The first node will jump to the last bug step.
    bugTree.click({ selector: "@bugStep", index: 0 });
    browser.assert.ok(await reportDetailPage.isCurrentReportStep(1));

    // Open first bug step.
    bugTree.click({ selector: "@bugStep", index: 1 });
    browser.assert.ok(await reportDetailPage.isCurrentReportStep(0));

    // Open the second bug step.
    bugTree.click({ selector: "@bugStep", index: 2 });
    browser.assert.ok(await reportDetailPage.isCurrentReportStep(1));
  },

  "open another bug" (browser) {
    const reportDetailPage = browser.page.reportDetail();
    const bugTree = reportDetailPage.section.bugTree;

    const oldOutstandingStateIndex = 2;
    const outstandingStateIndex = 1;
    const oldSeverityIndex = 1;
    const oldBugIndex = 1;
    const severityIndex = 2;
    const bugIndex = 1;
    const stepIndex = 1;

    bugTree.click(bugTree.getTreeNodeSelector(
      oldOutstandingStateIndex,
      oldSeverityIndex,
      oldBugIndex
    ));

    bugTree.click(bugTree.getTreeNodeSelector(
      oldOutstandingStateIndex,
      oldSeverityIndex
    ));

    bugTree.click(bugTree.getTreeNodeSelector(oldOutstandingStateIndex));

    bugTree.click(bugTree.getTreeNodeSelector(outstandingStateIndex));

    bugTree.click(bugTree.getTreeNodeSelector(
      outstandingStateIndex,
      severityIndex
    ));

    bugTree.click(bugTree.getTreeNodeSelector(
      outstandingStateIndex,
      severityIndex,
      bugIndex
    ));

    bugTree.click(bugTree.getTreeNodeSelector(
      outstandingStateIndex,
      severityIndex,
      bugIndex,
      stepIndex
    ));

    reportDetailPage.waitForProgressBarNotPresent();
  }
}
