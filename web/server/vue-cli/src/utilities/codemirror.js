import { cpp } from "@codemirror/lang-cpp";
import { go } from "@codemirror/lang-go";
import { java } from "@codemirror/lang-java";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";

/**
 * Returns the CodeMirror language extension for the given source file path.
 * C/C++ is the default language.
 */
export function getLanguageExtension(filePath) {
  const ext = (filePath || "").split(".").pop().toLowerCase();
  switch (ext) {
  case "py": return python();
  case "java": return java();
  case "js": case "jsx": case "mjs": return javascript();
  case "ts": case "tsx": return javascript({ typescript: true });
  case "go": return go();
  default: return cpp();
  }
}
