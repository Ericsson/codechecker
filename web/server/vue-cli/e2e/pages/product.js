const commands = {
  setAnnouncement(value) {
    this
      .click("@editAnnouncementBtn");

    this.expect.section("@editAnnouncementDialog")
      .to.be.visible.before(5000);

    this.section.editAnnouncementDialog
      .clearAndSetValue("@input", value, this.section.editAnnouncementDialog)
      .click("@confirmBtn");

    this.expect.section("@editAnnouncementDialog")
      .to.not.be.present.before(5000);

    return this;
  },

  showGlobalPermissionsDialog() {
    this
      .click("@editGlobalPermissionBtn");

    this.expect.section("@editGlobalPermissionsDialog")
      .to.be.visible.before(5000);

    return this;
  },

  closeGlobalPermissionsDialog() {
    this.section.editGlobalPermissionsDialog.click("@closeBtn");

    this.expect.section("@editGlobalPermissionsDialog")
      .to.not.be.present.before(5000);

    return this;
  },

  addNewGlobalPermissions(users=[], groups=[]) {
    const section = this.section.editGlobalPermissionsDialog;

    users.forEach(user => {
      section
        .clearAndSetValue("@userName", user, section)
        .click("@addNewUserBtn");
    });

    groups.forEach(group => {
      section
        .clearAndSetValue("@groupName", group, section)
        .click("@addNewGroupBtn");
    });

    return this;
  },

  togglePermissions() {
    const section = this.section.editGlobalPermissionsDialog;

    section.api.elements("@checkBox", (response) => {
      response.result.value.map(c => section.api.elementIdClick(
        c.ELEMENT || c["element-6066-11e4-a52e-4f735466cecf"]));
    });

    return this;
  },

  confirmChangeGlobalPermissions() {
    this.section.editGlobalPermissionsDialog
      .click("@confirmBtn");
    return this;
  },

  cancelChangeGlobalPermissions() {
    this.section.editGlobalPermissionsDialog
      .click("@cancelBtn");
    return this;
  },

  showNewProductDialog() {
    this
      .click("@newProductBtn");

    this.expect.section("@productDialog").to.be.visible;

    return this;
  },

  closeNewProductDialog() {
    this.section.productDialog
      .waitForElementVisible("@closeBtn")
      .click("@closeBtn", () => {
        this.expect.section("@productDialog").to.not.be.present.before(4000);
      });

    return this;
  },

  fillNewProductData(props={}) {
    const section = this.section.productDialog;

    if (props.endpoint !== undefined)
      section.clearAndSetValue("@endpoint", props.endpoint, section);

    if (props.displayName !== undefined)
      section.clearAndSetValue("@displayName", props.displayName, section);

    if (props.description !== undefined)
      section.clearAndSetValue("@description", props.description, section);

    if (props.runLimit !== undefined)
      section.clearAndSetValue("@runLimit", props.runLimit, section);

    if (props.disableReviewStatusChange !== undefined) {
      section.click("@disableReviewStatusChange");

      section.setCheckboxValue("@disableReviewStatusChange",
        props.disableReviewStatusChange, section);
    }

    if (props.engine === "sqlite") {
      if (props.dbFile !== undefined) {
        section
          .click("@sqlite")
          .clearAndSetValue("@dbFile", props.dbFile, section);
      }
    } else if (props.engine === "postgresql") {
      section.click("@postgresql");

      if (props.dbHost !== undefined)
        section.clearAndSetValue("@dbHost", props.dbHost, section);

      if (props.dbPort !== undefined)
        section.clearAndSetValue("@dbPort", props.dbPort, section);

      if (props.dbUsername !== undefined)
        section.clearAndSetValue("@dbUsername", props.dbUsername, section);

      if (props.dbPassword !== undefined)
        section.clearAndSetValue("@dbPassword", props.dbPassword, section);

      if (props.dbName !== undefined)
        section.clearAndSetValue("@dbName", props.dbName, section);
    }

    return this;
  },

  saveProduct() {
    this.section.productDialog
      .click("@confirmBtn");

    return this;
  },

  removeProduct() {
    this.click("@removeBtn");

    this.expect.section("@removeProductDialog").to.be.visible.before(5000);

    this.section.removeProductDialog
      .waitForElementVisible("@confirmBtn")
      .click("@confirmBtn");

    return this;
  },

  editProduct() {
    this
      .waitForElementVisible("@editBtn")
      .click("@editBtn");

    this.expect.section("@productDialog").to.be.visible.before(5000);

    return this;
  },

  filterProducts(search) {
    return this.clearAndSetValue("@searchInput", search)
      .waitForElementNotPresent("@progressBar", 5000)
      .pause(3000);
  },

  sortProducts(column, isSorted) {
    this
      .click({ selector: "th", index: column })
      .pause(500) // Wait some time to make sure progressbar appeared.
      .waitForElementNotPresent("@progressBar");

    this.getTableRows("@tableRows", (data) => {
      this.api.assert.ok(isSorted(data), "runs are not sorted");
    });

    return this;
  }
};

module.exports = {
  url: function() { 
    return this.api.launchUrl + '/'; 
  },
  commands: [ commands ],
  elements: {
    page: ".v-data-table",
    editAnnouncementBtn: "#edit-announcement-btn",
    editGlobalPermissionBtn: "#edit-global-permissions-btn",
    newProductBtn: "#new-product-btn",
    productRows: "table tbody > tr",
    emptyTable: ".v-data-table__empty-wrapper",
    tableRows: "tbody tr",
    searchInput: ".v-toolbar__content input[type='text']",
    progressBar: ".v-data-table__progress",
    editBtn: "tr .edit-btn",
    removeBtn: "tr .remove-btn"
  },
  sections: {
    editAnnouncementDialog: {
      selector: ".v-dialog__content--active .v-dialog",
      elements: {
        input: "input[type='text']",
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn"
      }
    },
    editGlobalPermissionsDialog: {
      selector: ".v-dialog__content--active .v-dialog",
      elements: {
        userName: ".col:nth-child(1) input[type='text']",
        addNewUserBtn: ".col:nth-child(1) button",
        users: ".col:nth-child(1) tbody > tr",
        groupName: ".col:nth-child(2) input[type='text']",
        addNewGroupBtn: ".col:nth-child(2) button",
        groups: ".col:nth-child(2) tbody > tr",
        checkBox: ".v-input--checkbox",
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn",
        closeBtn: ".title button"
      }
    },
    productDialog: {
      selector: ".v-dialog__content--active .v-card",
      elements: {
        endpoint: "input[name='endpoint']",
        displayName: "input[name='display-name']",
        description: "textarea[name='description']",
        runLimit: "input[name='run-limit']",
        disableReviewStatusChange: ".v-input--checkbox",
        sqlite: ".v-radio:nth-child(1)",
        postgresql: ".v-radio:nth-child(2)",
        dbFile: "input[name='db-file']",
        dbHost: "input[name='db-host']",
        dbPort: "input[name='db-port']",
        dbUsername: "input[name='db-username']",
        dbPassword: "input[name='db-password']",
        dbName: "input[name='db-name']",
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn",
        closeBtn: ".title button"
      }
    },
    removeProductDialog: {
      selector: ".v-dialog__content--active .v-card",
      elements: {
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn"
      }
    }
  }
}
