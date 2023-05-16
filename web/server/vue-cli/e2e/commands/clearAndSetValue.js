module.exports.command = function (selector, value, section) {
  // setValue() command is not clearing value first. 
  // https://github.com/nightwatchjs/nightwatch/issues/4
  if (section === undefined)
    section = this;

  return section
    // This pause(100) is required to make sure the element
    // is visible before clicking it.
    .pause(100)
    .click(selector)
    .getValue(selector, function (result) {
      section.setValue(selector, [
        this.Keys.CONTROL,
        "a",
        this.Keys.DELETE,
      ])
      section.setValue(selector, value);
    });
};
