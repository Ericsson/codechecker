/**
 * Returns the value of a CSS custom property from :root.
 * @param {string} name - The variable name (e.g. "color-error").
 * @returns {string} The trimmed CSS value.
 */
export function getCssColor(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(`--${name}`).trim();
}
