const commands = {
  setAnnouncement(value) {
    this
      .click("@editAnnouncementBtn");

    this.expect.section("@editAnnouncementDialog").to.be.visible;

    this.section.editAnnouncementDialog
      .clearAndSetValue("@input", value, this.section.editAnnouncementDialog)
      .click("@confirmBtn");

    this.expect.section("@editAnnouncementDialog").to.be.not.visible;

    return this;
  },

  showGlobalPermissionsDialog() {
    this
      .click("@editGlobalPermissionBtn");

    this.expect.section("@editGlobalPermissionsDialog").to.be.visible;

    return this;
  },

  closeGlobalPermissionsDialog() {
    this.section.editGlobalPermissionsDialog.click("@closeBtn");

    this.expect.section("@editGlobalPermissionsDialog").to.be.not.visible;

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
      response.result.value.map(c => section.api.elementIdClick(c.ELEMENT));
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
    newProductBtn: "#new-product-btn"
  },
  sections: {
    editAnnouncementDialog: {
      selector: ".v-dialog",
      elements: {
        input: "input[type='text']",
        cancelBtn: ".cancel-btn",
        confirmBtn: ".confirm-btn"
      }
    },
    editGlobalPermissionsDialog: {
      selector: ".v-dialog",
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
    }
  }
}
