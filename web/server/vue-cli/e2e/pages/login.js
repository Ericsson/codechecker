const commands = {
  login(username, password) {
    return this.waitForElementVisible("body")
      .setValue("@userName", username)
      .setValue("@password", password)
      .click("@submit");
  },

  loginAsAdmin() {
    return this.login("cc", "admin");
  },

  loginAsRoot() {
    return this.login("root", "S3cr3t");
  }
};

module.exports = {
  url: function() { 
    return this.api.launchUrl + '/login'; 
  },
  commands: [ commands ],
  elements: {
    userName: "input[name='username']",
    password: "input[name='password']",
    submit: "#login-btn",
    notificationTitle: ".notification-toast__title",
    notificationMessage: ".notification-toast__message",
    userNameErrorMessages: ".v-input:nth-child(1) .v-messages",
    passwordErrorMessages: ".v-input:nth-child(2) .v-messages"
  }
}
