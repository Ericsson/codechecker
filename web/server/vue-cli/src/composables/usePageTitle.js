import { ref } from "vue";

const TITLE_SUFFIX = "CodeChecker";

// Page specific part of the title (e.g. the currently viewed report). It is
// shared between the components which set it and the one which renders it.
const pageTitleDetail = ref(null);

export function buildPageTitle({ detail, page, product } = {}) {
  return [ detail, page, product, TITLE_SUFFIX ].filter(p => p).join(" - ");
}

export function buildReportTitle(filePath, line, checkerName) {
  if (!filePath) return null;

  const fileName = filePath.split(/[/\\]/).pop();
  return `${fileName}:${line} [${checkerName}]`;
}

export function usePageTitle() {
  return { pageTitleDetail };
}
