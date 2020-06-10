const idElements = (browser, element, selector) => {
  return new Promise((resolve, reject) => {
    const elementId = element.ELEMENT ||
      element["element-6066-11e4-a52e-4f735466cecf"];

    browser.elementIdElements(elementId, "css selector", selector,
      result => {
        if (result.status !== -1) {
          resolve(result.value);
        } else {
          reject(result);
        }
      });
  });
};

const text = (browser, element) => {
  const elementId = element.ELEMENT ||
      element["element-6066-11e4-a52e-4f735466cecf"];

  return new Promise((resolve, reject) => {
    browser.elementIdText(elementId, result => {
      if (result.status !== -1) {
        resolve(result.value);
      } else {
        reject(result);
      }
    });
  });
};

exports.command = function (selector, callback) {
  const getText = text.bind(null, this);
  this.elements("css selector", selector, result => {
    return Promise.all(result.value.map(element => {
      return idElements(this, element, "td, th").then(cells => {
        return Promise.all(cells.map(getText));
      }
      );
    }))
    .then(data => callback(data));
  });

  return this;
};
