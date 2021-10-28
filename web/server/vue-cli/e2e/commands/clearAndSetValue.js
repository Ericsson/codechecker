module.exports.command = function (selector, value, section) {
  // setValue() command is not clearing value first. 
  // https://github.com/nightwatchjs/nightwatch/issues/4
  if (section === undefined)
    section = this;

  return section
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
