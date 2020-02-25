module.exports = {
  root: true,
  env: {
    node: true
  },
  extends: [
    "plugin:vue/recommended",
    "eslint:recommended"
  ],
  rules: {
    "array-bracket-spacing": ["error", "always"],
    "no-console": process.env.NODE_ENV === "production" ? "error" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "error" : "off",
    "vue/max-attributes-per-line": "off",
    "quotes": ["error", "double", {
      "avoidEscape": true
    }]
  },
  parserOptions: {
    parser: "babel-eslint",
    sourceType: "module"
  }
}
