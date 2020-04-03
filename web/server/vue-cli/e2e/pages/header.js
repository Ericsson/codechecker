const commands = {
  logout() {
    return this
      .click("@userInfoMenuBtn")
      .click("@logOutBtn");
  }
};

module.exports = {
  commands: [ commands ],
  elements: {
    announcementAppBar: ".v-system-bar",
    userInfoMenuBtn: "#user-info-menu-btn",
    logOutBtn: "#logout-btn"
  }
};
