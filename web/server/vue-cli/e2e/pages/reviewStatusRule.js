const commands = {
  waitForProgressBarNotPresent() {
    this.pause(500, () => {
      this.waitForElementNotPresent("@progressBar");
    });
    return this;
  },
};

module.exports = {
  url: function() {
    return `${this.api.launchUrl}/e2e/review-status-rules`;
  },
  elements: {
    page: "#app",
    overlay: ".v-overlay.v-overlay--active",
    progressBar: ".v-data-table__progress",
    clearAllFiltersBtn: ".clear-all-filters-btn",
    newReviewStatusRuleBtn: ".new-rule-btn",
    removeFilteredRulesBtn: ".remove-filtered-rules-btn",
    editReviewStatusRuleBtn: ".edit-btn",
    removeReviewStatusRuleBtn: ".remove-btn",
  },
  commands: [ commands ],
  sections: {
    editReviewStatusRuleDialog: {
      selector: ".edit-review-status-rule-dialog.v-dialog--active",
      elements: {
        reportHash: ".report-hash input[type='text']",
        selectReviewStatus: ".select-review-status",
        message: "textarea[name='reviewStatusMessage']",
        confirmBtn: ".confirm-btn"
      }
    },
    removeReviewStatusRuleDialog: {
      selector: ".remove-review-status-rule-dialog.v-dialog--active",
      elements: {
        confirmBtn: ".confirm-btn"
      }
    },
    removeFilteredRulesDialog: {
      selector: ".remove-filtered-rules-dialog.v-dialog--active",
      elements: {
        confirmBtn: ".confirm-btn"
      }
    },
    selectReviewStatusMenu: {
      selector: ".select-review-status-menu.menuable__content__active",
      elements: {
        item: ".v-list-item"
      }
    },
    filters: {
      selector: ".review-status-rule-filters",
      elements: {
        reportHash: ".report-hash input[type='text']",
        author: ".author input[type='text']",
        selectReviewStatus: ".select-review-status",
        noAssociatedReports: ".no-associated-reports"
      }
    }
  }
}
