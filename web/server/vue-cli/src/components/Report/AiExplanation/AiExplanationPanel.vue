<template>
  <!-- Only DOMPurify sanitized answers are bound with v-html. -->
  <!-- eslint-disable vue/no-v-html -->
  <v-card
    class="ai-explanation-panel d-flex flex-column"
    variant="flat"
    height="100%"
  >
    <v-card-title class="d-flex align-center py-2 px-3">
      <v-icon size="small" color="primary" class="mr-2">
        mdi-lightbulb-on-outline
      </v-icon>

      <span class="text-body-2 font-weight-medium">
        AI explanation
      </span>

      <v-spacer />

      <!-- Switches the panel to the model list, to ask another model. -->
      <v-btn
        v-if="!expertMode"
        class="expert-mode-btn mr-1"
        size="x-small"
        density="compact"
        variant="text"
        title="Explain with another model"
        @click="openExpertMode"
      >
        <v-icon size="x-small" class="mr-1">
          mdi-tune-variant
        </v-icon>
        Expert mode
      </v-btn>
      <v-btn
        v-else
        class="expert-mode-btn mr-1"
        size="x-small"
        density="compact"
        variant="text"
        title="Back to the explanation"
        @click="expertMode = false"
      >
        <v-icon size="x-small" class="mr-1">
          mdi-arrow-left
        </v-icon>
        Back
      </v-btn>

      <v-btn
        class="close-btn"
        icon
        size="x-small"
        variant="text"
        title="Close"
        @click="$emit('close')"
      >
        <v-icon size="small">
          mdi-close
        </v-icon>
      </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="ai-explanation-content pa-0 flex-grow-1">
      <!-- Expert mode: choose the model. -->
      <div v-if="expertMode" class="chooser pa-4">
        <p class="text-body-2 mb-1">
          Which model should explain this report?
        </p>
        <p class="text-caption text-grey mb-4">
          EricAI models are listed while EricAI has them loaded; the others
          are asked directly at their provider.
        </p>

        <div v-if="!models.length" class="text-caption text-grey">
          {{ modelsMessage }}
        </div>

        <div v-else class="d-flex flex-column ga-2">
          <v-card
            v-for="model in models"
            :key="model.id"
            class="model-choice pa-3"
            :class="{ current: model.id === selectedModel }"
            variant="outlined"
            @click="chooseModel(model.id)"
          >
            <div class="d-flex align-center">
              <span class="text-body-2 font-weight-medium">
                {{ model.displayName }}
              </span>
              <v-chip
                v-if="model.isDefault"
                size="x-small"
                variant="tonal"
                class="ml-2"
              >
                default
              </v-chip>
              <v-chip
                size="x-small"
                variant="outlined"
                class="ml-auto"
                :title="providerOf(model).title"
              >
                <v-icon start size="x-small">
                  {{ providerOf(model).icon }}
                </v-icon>
                {{ providerOf(model).label }}
              </v-chip>
            </div>

            <div class="d-flex flex-wrap align-center ga-3 mt-2">
              <div class="rating">
                <span class="text-caption text-grey mr-1">Speed</span>
                <v-chip
                  size="x-small"
                  variant="tonal"
                  :color="speedOf(model).color"
                >
                  <v-icon start size="x-small">
                    {{ speedOf(model).icon }}
                  </v-icon>
                  {{ speedOf(model).label }}
                </v-chip>
              </div>

              <div class="rating">
                <span class="text-caption text-grey mr-1">Reliability</span>
                <v-chip
                  size="x-small"
                  variant="tonal"
                  :color="reliabilityOf(model).color"
                >
                  <v-icon start size="x-small">
                    {{ reliabilityOf(model).icon }}
                  </v-icon>
                  {{ reliabilityOf(model).label }}
                </v-chip>
              </div>
            </div>
          </v-card>
        </div>
      </div>

      <!-- Generating. -->
      <div
        v-else-if="loading || !explanation && !error"
        class="d-flex flex-column align-center justify-center pa-6"
      >
        <v-progress-circular indeterminate color="primary" size="36" />
        <div class="text-body-2 mt-3">
          <template v-if="selectedModel">
            Asking {{ selectedModelName }}&hellip;
          </template>
          <template v-else>
            Asking the default model&hellip;
          </template>
        </div>
        <div class="text-caption text-grey mt-1 text-center">
          This usually takes 5 - 20 seconds. The report, its bug path and
          the surrounding source are sent to {{ selectedProviderName }}.
        </div>
      </div>

      <!-- Failed. -->
      <v-alert
        v-else-if="error"
        class="ma-3"
        type="error"
        variant="tonal"
        density="compact"
      >
        {{ error }}
      </v-alert>

      <!-- Answered. Line numbers in it are buttons; see linkLines(). -->
      <div v-else class="pa-3" @click="onAnswerClick">
        <div class="d-flex align-center flex-wrap ga-2 mb-3">
          <v-chip
            class="verdict-chip"
            :color="verdictColor"
            variant="flat"
            size="small"
          >
            <v-icon start size="small">
              {{ verdictIcon }}
            </v-icon>
            {{ verdictLabel }}
          </v-chip>

          <v-chip size="small" variant="tonal">
            Confidence {{ explanation.confidence }}%
          </v-chip>
        </div>

        <section class="mb-4">
          <h4 class="text-caption text-uppercase text-grey mb-1">
            Background
          </h4>
          <div class="ai-html text-body-2" v-html="explanation.background" />
        </section>

        <section v-if="explanation.truePositiveCase" class="mb-4">
          <h4 class="text-caption text-uppercase text-grey mb-1">
            <v-icon size="x-small" color="error" class="mr-1">
              mdi-alert-circle-outline
            </v-icon>
            Why this may be a real defect
          </h4>
          <div
            class="ai-html text-body-2"
            v-html="explanation.truePositiveCase"
          />
        </section>

        <section v-if="explanation.falsePositiveCase" class="mb-4">
          <h4 class="text-caption text-uppercase text-grey mb-1">
            <v-icon size="x-small" color="success" class="mr-1">
              mdi-shield-check-outline
            </v-icon>
            Why this may be a false positive
          </h4>
          <div
            class="ai-html text-body-2"
            v-html="explanation.falsePositiveCase"
          />
        </section>

        <v-divider class="my-3" />

        <p class="text-caption text-grey mb-0">
          Generated by {{ selectedModelName }}. AI answers can be wrong -
          confirm against the code before setting a review status.
        </p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import DOMPurify from "dompurify";
import { computed, onMounted, ref, watch } from "vue";

import { ccService, handleThriftError } from "@cc-api";
import { AIVerdict } from "@cc/report-server-types";

const props = defineProps({
  reportId: { type: Object, default: null }
});

const emit = defineEmits([ "close", "go-to-line" ]);

const models = ref([]);
const selectedModel = ref(null);
const explanation = ref(null);
const loading = ref(false);
const error = ref(null);
const modelsMessage = ref("Loading models\u2026");
const expertMode = ref(false);

// How the administrator rated each model; see "speed" and "reliability"
// in the server configuration.
const SPEEDS = {
  fast: { label: "Fast", color: "success", icon: "mdi-speedometer" },
  medium: { label: "Medium", color: "warning", icon: "mdi-speedometer-medium" },
  slow: { label: "Slow", color: "error", icon: "mdi-speedometer-slow" }
};

const RELIABILITIES = {
  high: { label: "High", color: "success", icon: "mdi-shield-check-outline" },
  medium: { label: "Medium", color: "warning", icon: "mdi-shield-half-full" },
  low: { label: "Low", color: "error", icon: "mdi-shield-alert-outline" }
};

const NOT_RATED = { label: "Not rated", color: "grey", icon: "mdi-minus" };

// Unknown providers are shown under their own name.
const PROVIDERS = {
  ericai: { label: "EricAI", icon: "mdi-domain" },
  anthropic: { label: "Anthropic" },
  gemini: { label: "Google" },
  vertex_ai: { label: "Google Vertex AI" },
  openai: { label: "OpenAI" },
  azure: { label: "Azure OpenAI" },
  deepseek: { label: "DeepSeek" },
  mistral: { label: "Mistral" },
  ollama: { label: "Ollama", icon: "mdi-server" }
};

function providerOf(model) {
  // Older servers only offer EricAI models.
  const id = model.provider || "ericai";
  const known = PROVIDERS[id] || { label: id };
  const direct = id !== "ericai";

  return {
    label: known.label,
    icon: known.icon || "mdi-cloud-outline",
    title: direct ? `Asked directly at ${known.label}` : "Asked through EricAI"
  };
}

function speedOf(model) {
  return SPEEDS[model.speed] || NOT_RATED;
}

function reliabilityOf(model) {
  return RELIABILITIES[model.reliability] || NOT_RATED;
}

// Before Expert mode has fetched the list, only the model id is known.
const selectedModelName = computed(() => {
  const model = models.value.find(m => m.id === selectedModel.value);
  return model ? model.displayName : selectedModel.value;
});

const selectedProviderName = computed(() => {
  const model = models.value.find(m => m.id === selectedModel.value);
  return model ? providerOf(model).label : "the model's provider";
});

// The answer is HTML written by a model that has read untrusted source code,
// so treat it as hostile: keep only the formatting tags the prompt asks for,
// and no attributes at all. DOMPurify's defaults would still allow e.g.
// <img src>, which can send data to another server without any script.
const SANITIZE_OPTIONS = {
  ALLOWED_TAGS: [
    "p", "ul", "ol", "li", "strong", "em", "code", "pre", "br"
  ],
  ALLOWED_ATTR: []
};

const verdictLabel = computed(() => {
  switch (explanation.value?.verdict) {
  case AIVerdict.LIKELY_TRUE_POSITIVE:
    return "Likely a true positive";
  case AIVerdict.LIKELY_FALSE_POSITIVE:
    return "Likely a false positive";
  default:
    return "Uncertain";
  }
});

const verdictColor = computed(() => {
  switch (explanation.value?.verdict) {
  case AIVerdict.LIKELY_TRUE_POSITIVE:
    return "error";
  case AIVerdict.LIKELY_FALSE_POSITIVE:
    return "success";
  default:
    return "grey";
  }
});

const verdictIcon = computed(() => {
  switch (explanation.value?.verdict) {
  case AIVerdict.LIKELY_TRUE_POSITIVE:
    return "mdi-alert-circle-outline";
  case AIVerdict.LIKELY_FALSE_POSITIVE:
    return "mdi-shield-check-outline";
  default:
    return "mdi-help-circle-outline";
  }
});

// Opening the panel is the request: explain right away. Without a model the
// server uses its default, so the model list is not needed for this.
onMounted(() => explain());

// Never leave an answer next to a different report. Compared by value: the
// same report reloaded (e.g. after a review status change) keeps its answer.
watch(() => props.reportId?.toString(), (id, previousId) => {
  if (id === previousId) return;

  expertMode.value = false;
  reset();
  explain();
});

// Only the latest request may show its answer; an earlier one may still be
// running for another report or model.
let latestRequest = 0;

function reset() {
  latestRequest++;
  explanation.value = null;
  error.value = null;
  loading.value = false;
  selectedModel.value = null;
}

// The loaded EricAI models change over time, so the list is asked for each
// time Expert mode opens. A failure keeps the list it has.
function openExpertMode() {
  expertMode.value = true;
  loadModels();
}

function chooseModel(modelId) {
  expertMode.value = false;
  explain(modelId);
}

function loadModels() {
  ccService.getClient().getAIModels(handleThriftError(availableModels => {
    if (availableModels.length) {
      models.value = availableModels;
    } else if (!models.value.length) {
      modelsMessage.value = "AI explanation is not enabled on this server.";
    }
  }, err => {
    if (!models.value.length) modelsMessage.value = errorMessage(err);
  }));
}

// An empty ``modelId`` asks the server's default model.
function explain(modelId = "") {
  if (!props.reportId) return;

  const request = ++latestRequest;

  selectedModel.value = modelId || null;
  loading.value = true;
  error.value = null;
  explanation.value = null;

  ccService.getClient().getReportExplanation(
    props.reportId,
    modelId,
    handleThriftError(result => {
      if (request !== latestRequest) return;
      selectedModel.value = result.model;
      explanation.value = {
        ...result,
        background: linkLines(
          DOMPurify.sanitize(result.background, SANITIZE_OPTIONS)),
        truePositiveCase: linkLines(
          DOMPurify.sanitize(result.truePositiveCase, SANITIZE_OPTIONS)),
        falsePositiveCase: linkLines(
          DOMPurify.sanitize(result.falsePositiveCase, SANITIZE_OPTIONS))
      };
      loading.value = false;
    }, err => {
      if (request !== latestRequest) return;
      error.value = errorMessage(err);
      loading.value = false;
    }));
}

// "line 16", "lines 11-16", "lines 3, 7 and 9", but not "line 42 of util.h":
// the model only saw the report's own file, so only those lines can be shown.
const LINE_REFERENCE = new RegExp(
  "\\blines?\\s+\\d+(?:\\s*(?:,|-|\u2013|\u2014|to|and)\\s*\\d+)*" +
  "(?!\\d)(?!\\s+(?:of|in)\\s+[\\w./-]+\\.\\w+)", "gi");

// Turns the line numbers in already sanitized HTML into buttons. They are
// built here, never taken from the answer, and carry nothing but a number.
function linkLines(html) {
  const template = document.createElement("template");
  template.innerHTML = html;

  const walker = document.createTreeWalker(
    template.content, NodeFilter.SHOW_TEXT);
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);

  for (const text of texts) {
    const value = text.nodeValue;
    const matches = [ ...value.matchAll(LINE_REFERENCE) ];
    if (!matches.length) continue;

    const fragment = document.createDocumentFragment();
    let last = 0;

    for (const match of matches) {
      fragment.append(value.slice(last, match.index));

      let pos = 0;
      for (const number of match[0].matchAll(/\d+/g)) {
        fragment.append(match[0].slice(pos, number.index));

        const button = document.createElement("button");
        button.type = "button";
        button.className = "ai-line-ref";
        button.dataset.line = number[0];
        button.title = `Go to line ${number[0]}`;
        button.textContent = number[0];
        fragment.append(button);

        pos = number.index + number[0].length;
      }

      fragment.append(match[0].slice(pos));
      last = match.index + match[0].length;
    }

    fragment.append(value.slice(last));
    text.replaceWith(fragment);
  }

  return template.innerHTML;
}

function onAnswerClick(event) {
  const button = event.target.closest?.(".ai-line-ref");
  if (button) emit("go-to-line", Number(button.dataset.line));
}

function errorMessage(err) {
  return err?.message || "The explanation could not be generated.";
}
</script>

<style lang="scss" scoped>
.ai-explanation-panel {
  border-left: 1px solid rgb(var(--v-border-color), 0.2);
  overflow: hidden;
}

.ai-explanation-content {
  overflow-y: auto;
}

.expert-mode-btn {
  font-size: 0.7rem;
  letter-spacing: normal;
  text-transform: none;
  opacity: 0.8;
}

.model-choice.current {
  border-color: rgb(var(--v-theme-primary));
}

.rating {
  display: flex;
  align-items: center;
}

.ai-html {
  :deep(p),
  :deep(ul),
  :deep(ol),
  :deep(pre) {
    margin-bottom: 8px;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 20px;
  }

  :deep(code),
  :deep(pre) {
    font-family: monospace;
    background: rgba(var(--v-theme-on-surface), 0.06);
    border-radius: 3px;
  }

  :deep(code) {
    padding: 0 3px;
  }

  :deep(pre) {
    padding: 6px 8px;
    white-space: pre-wrap;
    overflow-x: auto;
  }

  :deep(pre code) {
    padding: 0;
    background: none;
  }

  > :deep(:last-child) {
    margin-bottom: 0;
  }

  :deep(.ai-line-ref) {
    padding: 0 1px;
    border: none;
    background: none;
    color: rgb(var(--v-theme-primary));
    font: inherit;
    text-decoration: underline dotted;
    text-underline-offset: 2px;
    cursor: pointer;

    &:hover,
    &:focus-visible {
      text-decoration-style: solid;
    }
  }
}
</style>
