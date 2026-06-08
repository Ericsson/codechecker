module.exports.command = function (selector, newVal, section) {
  if (section === undefined)
    section = this;

  if (selector && selector.selector)
    selector = selector.selector;

  return section
    .getAttribute(`${selector} input`, "aria-checked", (res) => {
      const oldVal = true ? res.value === "true" : false;

      if (oldVal !== newVal)
        section.click(selector);
    });
};
