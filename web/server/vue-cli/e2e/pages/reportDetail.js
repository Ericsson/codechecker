const commands = {
  waitForProgressBarNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@progressBar");
    });
    return this;
  },

  async isCurrentReportStep(index) {
    const elements = await this.api.elements("@reportStepMsg");

    const value = elements.value[index];
    const elementId = value.ELEMENT ||
      value["element-6066-11e4-a52e-4f735466cecf"];

    const element = await this.api.elementIdAttribute(elementId, "class");

    return element.value.split(" ").includes("current");
  }
};

const commentsPaneCommands = {
  waitForOverlayNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@overlay");
    });
    return this;
  }
};

const bugTreeCommands = {
  node(index) {
    return `${this.elements.node.selector}:nth-child(${index})`;
  },

  getTreeNodeSelector(severityIndex, bugIndex, stepIndex) {
    let selectors = [ this.selector, ">", this.node(severityIndex) ];

    if (bugIndex !== undefined) {
      selectors.push(
        ...[ ">", this.elements.childNode.selector, this.node(bugIndex)]);

      if (stepIndex !== undefined) {
        selectors.push(
          ...[">", this.elements.childNode.selector, this.node(stepIndex)]);
      }
    }

    selectors.push(this.elements.rootNode.selector);

    return selectors.join(" ");
  }
};

module.exports = {
  url: function() {
    return this.api.launchUrl
      + "/e2e/report-detail?report-hash=0db7fdfc2bc9d487ca571fbbb68029cc"; 
  },
  elements: {
    page: ".container",
    showDocumentationBtn: ".show-documentation-btn",
    progressBar: "#editor-wrapper .v-progress-linear",
    selectReviewStatus: ".select-review-status",
    reviewStatusMessage: ".review-status-message",
    commentsBtn: ".comments-btn",
    selectSameReport: ".select-same-report",
    reportStepMsg: ".report-step-msg"
  },
  commands: [ commands ],
  sections: {
    documentationDialog: {
      selector: ".documentation-dialog.v-dialog--active",
      elements: {
        closeBtn: ".close-btn",
        content: ".container"
      }
    },
    selectReviewStatusMenu: {
      selector: ".select-review-status-menu",
      elements: {
        item: ".v-list-item"
      }
    },
    changeReviewStatusMessageDialog: {
      selector: ".select-review-status-dialog.v-dialog--active",
      elements: {
        message: "textarea",
        save: ".save-btn"
      }
    },
    reviewStatusMessageMenu: {
      selector: ".review-status-message-dialog.menuable__content__active",
      elements: {
        message: ".v-list:last-child .v-list-item__title"
      }
    },
    commentsPane: {
      selector: ".comments",
      elements: {
        message: "textarea",
        addBtn: ".new-comment-btn",
        overlay: ".v-overlay.v-overlay--active"
      },
      commands: [ commentsPaneCommands ],
      sections: {
        userComment: {
          selector: ".user-comment",
          elements: {
            editBtn: ".edit-btn",
            removeBtn: ".remove-btn",
            message: ".v-card__text"
          }
        },
        systemComment: {
          selector: ".system-comment",
          elements: {
            message: ".v-card__text"
          }
        }
      }
    },
    editCommentDialog: {
      selector: ".edit-comment-dialog.v-dialog--active",
      elements: {
        message: "textarea",
        saveBtn: ".save-btn"
      }
    },
    removeCommentDialog: {
      selector: ".remove-comment-dialog.v-dialog--active",
      elements: {
        removeBtn: ".remove-btn"
      }
    },
    selectSameReportMenu: {
      selector: ".select-same-report-menu.menuable__content__active",
      elements: {
        item: ".v-list-item"
      }
    },
    bugTree: {
      selector: ".v-treeview",
      elements: {
        bugStep: ".v-treeview-node--leaf",
        node: ".v-treeview-node",
        rootNode: ".v-treeview-node__root",
        childNode: ".v-treeview-node__children"
      },
      commands: [ bugTreeCommands ]
    }
  }
}
