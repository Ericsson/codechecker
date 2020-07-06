module.exports.command = function (selector, value, section) {
  // setValue() command is not clearing value first. 
  // https://github.com/nightwatchjs/nightwatch/issues/4
  if (section === undefined)
    section = this;

  return section
    .click(selector)
    .getValue(selector, function (result) {
      for (c in result.value) {
        section.setValue(selector, this.Keys.BACK_SPACE);
      }

      section.setValue(selector, value);
    });
};
