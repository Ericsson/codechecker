import { defineConfig } from "eslint/config";
import js from "@eslint/js";
import globals from "globals";
import pluginVue from "eslint-plugin-vue";
import vue from "eslint-plugin-vue";

const isProduction = process.env.NODE_ENV === 'production';

export default defineConfig([
  {
    ignores: [
      "node_modules/**",
      "dist/**"
    ]
  },
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: [
      "**/*.vue",
      "**/*.js"
    ],
    extends: [
      "js/recommended"
    ],
    plugins: {
      js
    },
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.browser,
        ...globals.jest
      }
    },
    rules: {
      "array-bracket-spacing": ["error", "always"],
      "arrow-parens": ["error", "as-needed"],
      "indent": ["error", 2],
      "keyword-spacing": ["error"],
      "max-len": ["error", { "code": 80 }],
      "no-console": isProduction ? [ "error", { "allow": ["warn"] } ]
        : "off",
      "no-debugger": isProduction ?  "error" : "off",
      "no-duplicate-imports": ["error", { "includeExports": true }],
      "object-curly-spacing": ["error", "always"],
      "prefer-const": ["error"],
      "semi": ["error", "always"],
      "sort-imports": ["error", { "ignoreDeclarationSort": true }],
      "vue/max-attributes-per-line": ["error", {
        "singleline": 20,
        "multiline": 1
      }],
      "vue/v-slot-style": "off",
      "vue/valid-v-slot": "off",
      "vue/multi-word-component-names": "off",
      "vue/no-mutating-props": "error",
      "vue/valid-next-tick": "off",
      "quotes": ["error", "double", {
        "avoidEscape": true
      }],
      "vue/component-api-style": ["warn", ["script-setup"]], // TODO: error
      "vue/block-order": ["warn", { // TODO: error
        "order": ["template", "script", "style"]
      }],
      "vue/define-macros-order": ["warn", { // TODO: error
        "order": ["defineProps", "defineEmits", "defineExpose"]
      }],
      "vue/no-ref-object-reactivity-loss": "warn",
      "vue/no-setup-props-reactivity-loss": "warn",
      "vue/prefer-define-options": "warn",
      "vue/require-macro-variable-name": ["warn", { // TODO: error
        "defineProps": "props",
        "defineEmits": "emit",
        "defineSlots": "slots",
        "useSlots": "slots",
        "useAttrs": "attrs"
      }]
    }
  }
]);
