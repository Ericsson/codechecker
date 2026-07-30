<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Code Coverage View
            <v-spacer />
            <!-- Breadcrumb Navigation (GCOV style) -->
            <div
              v-if="breadcrumbs.length > 0"
              class="breadcrumb-nav"
            >
              <span
                v-for="(crumb, idx) in breadcrumbs"
                :key="`crumb-${idx}`"
              >
                <router-link
                  v-if="crumb.to"
                  :to="crumb.to"
                  class="breadcrumb-link"
                >
                  {{ crumb.text }}
                </router-link>
                <span
                  v-else
                  class="breadcrumb-link breadcrumb-current"
                >
                  {{ crumb.text }}
                </span>
                <span
                  v-if="idx < breadcrumbs.length - 1"
                  class="breadcrumb-separator"
                >
                  / 
                </span>
              </span>
            </div>
            <v-btn
              v-if="sourceFile"
              icon
              small
              @click="goBack"
            >
              <v-icon>
                mdi-arrow-left
              </v-icon>
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-row v-if="!fileIdFromRoute">
              <v-col cols="12" md="6">
                <v-autocomplete
                  v-model="selectedFile"
                  :items="fileList"
                  :loading="loading"
                  :search-input.sync="fileSearchQuery"
                  :filter="filterFiles"
                  label="Search and select file"
                  item-text="name"
                  item-value="fileId"
                  return-object
                  clearable
                  @change="loadFile"
                >
                  <template v-slot:item="{ item }">
                    <v-list-item-content>
                      <v-list-item-title>
                        {{ item.name }}
                      </v-list-item-title>
                      <v-list-item-subtitle>
                        {{ item.path }}
                      </v-list-item-subtitle>
                    </v-list-item-content>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
            <!-- Coverage Summary Table (LCOV style) -->
            <v-row v-if="sourceFile" class="mb-4">
              <v-col cols="12">
                <div class="coverage-summary-wrapper">
                  <table class="coverage-summary-table">
                    <tbody>
                      <!-- Header row -->
                      <tr>
                        <td class="summary-header-item">
                          Current view:
                        </td>
                        <td class="summary-header-value">
                          <span class="breadcrumb-inline">
                            <router-link
                              :to="{
                                name: 'code-coverage-statistics',
                                query: {}
                              }"
                              class="breadcrumb-link-inline"
                            >
                              top level
                            </router-link>
                            <template
                              v-if="breadcrumbPathSegments &&
                                breadcrumbPathSegments.length > 0"
                            >
                              <span class="breadcrumb-separator-inline">
                                -
                              </span>
                              <template
                                v-for="(segment, idx) in breadcrumbPathSegments"
                              >
                                <router-link
                                  :key="`seg-${idx}`"
                                  :to="{
                                    name: 'code-coverage-statistics',
                                    query: { path: segment.path }
                                  }"
                                  class="breadcrumb-link-inline"
                                >
                                  {{ segment.name }}
                                </router-link>
                                <span
                                  v-if="idx < breadcrumbPathSegments.length - 1"
                                  :key="`sep-${idx}`"
                                  class="breadcrumb-separator-inline"
                                >
                                  -
                                </span>
                              </template>
                              <span class="breadcrumb-separator-inline">
                                -
                              </span>
                            </template>
                            <span class="breadcrumb-current-inline">
                              {{ currentFilePath.split('/').pop() }}
                            </span>
                            <span class="breadcrumb-meta">
                              (source / functions)
                            </span>
                          </span>
                        </td>
                        <td class="summary-spacer" />
                        <td class="summary-spacer" />
                        <td class="summary-header-cov">
                          Coverage
                        </td>
                        <td
                          class="summary-header-cov"
                          title="Covered + Uncovered code"
                        >
                          Total
                        </td>
                        <td
                          class="summary-header-cov"
                          title="Exercised code only"
                        >
                          Hit
                        </td>
                      </tr>
                      <!-- Test row -->
                      <tr>
                        <td class="summary-header-item">
                          Test:
                        </td>
                        <td class="summary-header-value">
                          coverage.json
                        </td>
                        <td class="summary-spacer" />
                        <td class="summary-label">
                          Lines:
                        </td>
                        <td
                          :class="getCoverageClass(lineCoverage)"
                          class="summary-cov-value"
                        >
                          {{ lineCoverage }}&nbsp;%
                        </td>
                        <td class="summary-cov-number">
                          {{ lineTotal }}
                        </td>
                        <td class="summary-cov-number">
                          {{ lineHit }}
                        </td>
                      </tr>
                      <!-- Test Date row -->
                      <tr>
                        <td class="summary-header-item">
                          Test Date:
                        </td>
                        <td class="summary-header-value">
                          {{ testDate || '' }}
                        </td>
                        <td class="summary-spacer" />
                        <td class="summary-label">
                          Functions:
                        </td>
                        <td
                          :class="getCoverageClass(functionCoverage)"
                          class="summary-cov-value"
                        >
                          {{ functionCoverage }}&nbsp;%
                        </td>
                        <td class="summary-cov-number">
                          {{ functionTotal }}
                        </td>
                        <td class="summary-cov-number">
                          {{ functionHit }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </v-col>
            </v-row>

            <!-- File Path Display -->
            <v-row v-if="sourceFile && !loading" class="mb-2">
              <v-col cols="12">
                <div class="file-path-display">
                  <v-icon
                    small
                    class="mr-2"
                  >
                    mdi-file-code
                  </v-icon>
                  <span class="file-path-text">{{ currentFilePath }}</span>
                </div>
              </v-col>
            </v-row>

            <!-- LCOV-style Line-by-Line Coverage View -->
            <v-row v-if="sourceFile && !loading" class="mt-2">
              <v-col cols="12">
                <div class="coverage-source-wrapper">
                  <pre class="source-heading">
                    <span class="line-data-header">Line data</span>
                    <span class="source-code-header">Source code</span>
                  </pre>
                  <pre class="source-content">
                    <span
                      v-for="(line, index) in sourceLines"
                      :id="'L' + (index + 1)"
                      :key="index"
                      class="source-line"
                    >
                      <span class="line-number">
                        {{ formatLineNumber(index + 1) }}
                      </span>
                      <span
                        :class="getLineDataClass(index + 1)"
                        class="line-data"
                      >
                        {{ getLineDataText(index + 1) }}
                      </span>
                      <span
                        :class="getLineSourceClass(index + 1)"
                        class="line-source"
                      >
                        {{ escapeHtml(line) }}
                      </span>
                    </span>
                  </pre>
                </div>
              </v-col>
            </v-row>

            <v-row
              v-else-if="sourceFile && loading"
              v-fill-height
              class="editor ma-0"
              style="min-height: 500px;"
            >
              <v-col cols="12">
                <v-progress-linear
                  indeterminate
                  class="mb-2"
                />
                <textarea ref="editor" style="display: none;" />
              </v-col>
            </v-row>

            <v-alert
              v-else-if="!loading"
              type="info"
              class="mt-4"
            >
              Please select a file to view coverage information.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/clike/clike.js";

import { FillHeight } from "@/directives";
import { ccService, handleThriftError } from "@cc-api";
import { Encoding } from "@cc/report-server-types";

export default {
  name: "CodeCoverageView",
  components: {},
  directives: { FillHeight },
  data() {
    return {
      editor: null,
      sourceFile: null,
      selectedFile: null,
      fileList: [],
      coveredLines: [],
      loading: false,
      fileSearchQuery: "",
      currentFilePath: "",
      sourceLines: []
    };
  },
  computed: {
    fileIdFromRoute() {
      return this.$route.query.fileId;
    },
    testDate() {
      try {
        if (this.sourceFile && this.sourceFile.storedAt) {
          return new Date(this.sourceFile.storedAt).toLocaleString();
        }
        return new Date().toLocaleString();
      } catch (e) {
        return new Date().toLocaleString();
      }
    },
    breadcrumbPathSegments() {
      try {
        // Get path from route query first
        let path = "";
        if (this.$route && this.$route.query && this.$route.query.path) {
          path = this.$route.query.path;
        } else if (this.currentFilePath) {
          // Derive path from file path
          // Extract directory path from full file path
          // Example: /Users/.../GCOV/test/test2.c -> /GCOV/test/
          const fileDir = this.currentFilePath.substring(
            0, this.currentFilePath.lastIndexOf("/"));
          
          // Find the base directory (e.g., "GCOV" or "test")
          // We want to show meaningful path segments
          const pathParts = fileDir.split("/").filter(p => p && p !== "");
          
          // Get the last 2-3 meaningful segments (e.g., ["GCOV", "test"])
          // This gives us the relevant directory structure
          if (pathParts.length >= 2) {
            // Take the last 2 segments
            const relevantParts = pathParts.slice(-2);
            path = "/" + relevantParts.join("/") + "/";
          } else if (pathParts.length === 1) {
            path = "/" + pathParts[0] + "/";
          }
        }
        
        if (!path) {
          return [];
        }
        
        // Normalize path: ensure it starts and ends with /
        let normalizedPath = path;
        if (!normalizedPath.startsWith("/")) {
          normalizedPath = "/" + normalizedPath;
        }
        if (!normalizedPath.endsWith("/")) {
          normalizedPath = normalizedPath + "/";
        }
        
        // Split into segments
        const segments = normalizedPath.split("/").filter(s => s && s !== "");
        const result = [];
        let currentPath = "";
        
        // Build cumulative paths for each segment
        // Each segment becomes a clickable link to that directory level
        segments.forEach(segment => {
          currentPath += "/" + segment;
          result.push({
            name: segment,
            path: currentPath + "/"
          });
        });
        
        return result;
      } catch (e) {
        return [];
      }
    },
    breadcrumbs() {
      if (!this.currentFilePath) {
        return [];
      }
      const path = this.$route.query.path || "";
      const crumbs = [];
      
      // Add "top level" link
      crumbs.push({
        text: "top level",
        to: {
          name: "code-coverage-statistics",
          query: {}
        }
      });
      
      // Add path segments if we're in a subdirectory
      if (path) {
        const segments = path.split("/").filter(s => s);
        let currentPath = "";
        segments.forEach(segment => {
          currentPath += "/" + segment;
          crumbs.push({
            text: segment,
            to: {
              name: "code-coverage-statistics",
              query: { path: currentPath + "/" }
            }
          });
        });
      }
      
      // Add current file name
      if (this.currentFilePath) {
        const fileName = this.currentFilePath.split("/").pop();
        crumbs.push({
          text: fileName,
          to: null // Current page, not a link
        });
      }
      
      return crumbs;
    },
    lineCoverage() {
      if (!this.coveredLines || this.coveredLines.length === 0) {
        return 0;
      }
      const covered = this.coveredLines.filter(l => l > 0).length;
      const uncovered = this.coveredLines.filter(l => l < 0).length;
      const total = covered + uncovered;
      return total > 0
        ? Math.round((covered / total) * 1000) / 10 : 0;
    },
    lineTotal() {
      if (!this.coveredLines) {
        return 0;
      }
      const covered = this.coveredLines.filter(l => l > 0).length;
      const uncovered = this.coveredLines.filter(l => l < 0).length;
      return covered + uncovered;
    },
    lineHit() {
      if (!this.coveredLines) {
        return 0;
      }
      return this.coveredLines.filter(l => l > 0).length;
    },
    functionCoverage() {
      // Calculate function coverage
      if (!this.sourceFile || !this.coveredLines) {
        return 0;
      }
      const stats = this.calculateFunctionCoverage(
        this.sourceFile.fileContent, this.coveredLines);
      return stats.rate;
    },
    functionTotal() {
      if (!this.sourceFile) {
        return 0;
      }
      const stats = this.calculateFunctionCoverage(
        this.sourceFile.fileContent, this.coveredLines);
      return stats.total;
    },
    functionHit() {
      if (!this.sourceFile || !this.coveredLines) {
        return 0;
      }
      const stats = this.calculateFunctionCoverage(
        this.sourceFile.fileContent, this.coveredLines);
      return stats.hit;
    }
  },
  watch: {
    "$route.query.fileId": {
      immediate: true,
      handler(newFileId) {
        if (newFileId) {
          this.loadFileFromRoute(newFileId);
        }
      }
    }
  },
  mounted() {
    this.loadFileList();
    if (this.fileIdFromRoute) {
      this.loadFileFromRoute(this.fileIdFromRoute);
    }
  },
  methods: {
    goBack() {
      // Navigate back to coverage statistics page
      const path = this.$route.query.path || "";
      this.$router.push({
        name: "code-coverage-statistics",
        query: path ? { path } : {}
      });
    },
    filterFiles(item, queryText) {
      const q = (queryText || "").toLowerCase();
      return item.name.toLowerCase().includes(q) ||
        item.path.toLowerCase().includes(q);
    },
    async loadFileList() {
      this.loading = true;
      try {
        const client = ccService.getClient();

        // Check if the function exists (Thrift API might not be
        // regenerated yet)
        if (typeof client.getFilesWithCoverage !== "function") {
          this.fileList = [];
          this.loading = false;
          return;
        }

        const files = await new Promise((resolve, reject) => {
          client.getFilesWithCoverage(
            handleThriftError(
              result => resolve(result),
              error => reject(error)
            )
          );
        });

        this.fileList = files.map(file => ({
          fileId: file.fileId,
          name: file.filePath.split("/").pop() || file.filePath,
          path: file.filePath
        }));
      } catch (error) {
        // Handle Thrift read errors gracefully
        if (error && error.message && error.message.includes("read")) {
          // Thrift API not regenerated - function doesn't exist
          this.fileList = [];
        } else {
          this.fileList = [];
        }
      } finally {
        this.loading = false;
      }
    },

    async loadFileFromRoute(fileIdStr) {
      const fileId = parseInt(fileIdStr, 10);
      if (!fileId || isNaN(fileId)) {
        return;
      }

      // Find file in fileList
      const file = this.fileList.find(f => f.fileId === fileId);
      if (file) {
        await this.loadFile(file);
      } else {
        // File not in list yet, try to load it directly
        await this.loadFileById(fileId);
      }
    },
    async loadFileById(fileId) {
      this.loading = true;
      try {
        const filePath = this.$route.query.filePath || "";
        this.currentFilePath = filePath;


        const [ sourceFile, coveredLines ] = await Promise.all([
          new Promise((resolve, reject) => {
            ccService.getClient().getSourceFileData(
              fileId,
              true,
              Encoding.DEFAULT,
              handleThriftError(
                result => resolve(result),
                error => reject(error)
              )
            );
          }),
          new Promise((resolve, reject) => {
            ccService.getClient().getTestCoverage(
              fileId,
              handleThriftError(
                result => resolve(result),
                error => reject(error)
              )
            );
          })
        ]);

        this.sourceFile = sourceFile;
        this.coveredLines = coveredLines.map(
          line => parseInt(line, 10)
        );

        // Initialize editor if not already initialized
        await this.$nextTick();
        if (!this.editor && this.$refs.editor) {
          this.editor = CodeMirror.fromTextArea(this.$refs.editor, {
            lineNumbers: true,
            readOnly: true,
            mode: "text/x-c++src",
            gutters: [ "CodeMirror-linenumbers" ],
            viewportMargin: 200
          });
          this.editor.setSize("100%", "100%");
        }

        if (this.editor) {
          this.editor.setValue(sourceFile.fileContent || "");
        }

        // Apply coverage highlights
        await this.applyCoverageHighlights();
      } catch (error) {
        // eslint-disable-next-line no-console
        console.debug("Error loading file:", error);
      } finally {
        this.loading = false;
      }
    },
    async loadFile(file) {
      if (!file || !file.fileId) {
        return;
      }

      this.currentFilePath = file.path;
      this.loading = true;
      try {
        const fileId = file.fileId;

        const [ sourceFile, coveredLines ] = await Promise.all([
          new Promise((resolve, reject) => {
            ccService.getClient().getSourceFileData(
              fileId,
              true,
              Encoding.DEFAULT,
              handleThriftError(
                result => resolve(result),
                error => reject(error)
              )
            );
          }),
          new Promise((resolve, reject) => {
            ccService.getClient().getTestCoverage(
              fileId,
              handleThriftError(
                result => resolve(result),
                error => reject(error)
              )
            );
          })
        ]);

        this.sourceFile = sourceFile;
        this.coveredLines = coveredLines.map(
          line => parseInt(line, 10)
        );
        this.sourceLines = sourceFile.fileContent
          ? sourceFile.fileContent.split("\n")
          : [];
      } catch (error) {
        // eslint-disable-next-line no-console
        console.debug("Error loading file:", error);
      } finally {
        this.loading = false;
      }
    },
    isExecutableLine(lineContent) {
      if (!lineContent) {
        return false;
      }

      const trimmed = lineContent.trim();
      
      // Empty lines are not executable
      if (trimmed === "") {
        return false;
      }

      // Comments are not executable
      if (trimmed.startsWith("//") || trimmed.startsWith("/*") || 
          trimmed.startsWith("*") || trimmed.startsWith("*/")) {
        return false;
      }

      // Preprocessor directives (includes, defines, etc.) are not executable
      if (trimmed.startsWith("#")) {
        return false;
      }

      // LCOV logic: Exclude standalone closing braces
      // Lines that are ONLY a closing brace are not counted as executable
      if (trimmed === "}" || trimmed === "};") {
        return false;
      }

      // LCOV logic: Exclude simple return statements
      // (return with just a variable)
      // But include return statements with expressions
      // (like "return a - b;")
      // Pattern: "return" followed by optional whitespace,
      // then identifier, then semicolon
      const simpleReturnPattern = /^\s*return\s+\w+\s*;?\s*$/;
      if (simpleReturnPattern.test(trimmed)) {
        return false;
      }

      // Everything else is considered executable
      return true;
    },
    getLineCoverageStatus(lineNum) {
      // Positive line numbers = covered (green)
      // Negative line numbers = uncovered/executable (red)
      // Absent = non-executable (white)
      const coveredSet = new Set(
        this.coveredLines.filter(l => l > 0));
      const uncoveredSet = new Set(
        this.coveredLines.filter(l => l < 0).map(l => -l));

      if (coveredSet.has(lineNum)) {
        return "covered";
      }
      if (uncoveredSet.has(lineNum)) {
        return "uncovered";
      }
      return "none";
    },
    async applyCoverageHighlights() {
      if (!this.editor || !this.sourceFile || !this.coveredLines) {
        return;
      }

      // Clear existing highlights
      this.clearCoverageHighlights();

      const totalLines = this.editor.lineCount();

      // Apply line highlights based on LCOV data
      this.editor.operation(() => {
        for (let i = 0; i < totalLines; i++) {
          const lineNum = i + 1;
          const status = this.getLineCoverageStatus(lineNum);

          // Only highlight executable lines
          if (status === "covered") {
            // Green: covered executable lines (like GCOV's tlaGNC, tlaCBC)
            this.editor.addLineClass(
              i, "background", "coverage-line-covered");
          } else if (status === "uncovered") {
            // Red: uncovered executable lines (like GCOV's tlaUNC)
            this.editor.addLineClass(
              i, "background", "coverage-line-uncovered");
          }
          // Non-executable lines (includes, comments, etc.) remain uncolored
          // (like GCOV's excluded lines)
        }
      });

      this.editor.refresh();
    },

    clearCoverageHighlights() {
      if (!this.editor) {
        return;
      }

      // Remove CSS classes from all lines
      const totalLines = this.editor.lineCount();
      this.editor.operation(() => {
        for (let i = 0; i < totalLines; i++) {
          this.editor.removeLineClass(i, "background",
            "coverage-line-covered");
          this.editor.removeLineClass(i, "background",
            "coverage-line-uncovered");
        }
      });
    },
    getCoverageClass(coverage) {
      // LCOV logic: High >= 80%, Medium 50-79%, Low < 50%
      if (coverage >= 80) {
        return "coverage-high";
      } else if (coverage >= 50) {
        return "coverage-medium";
      } else {
        return "coverage-low";
      }
    },
    formatLineNumber(lineNum) {
      // Format line number to match LCOV style (right-aligned, 8 spaces)
      return String(lineNum).padStart(8, " ");
    },
    getLineDataText(lineNum) {
      const coveredSet = new Set(
        this.coveredLines.filter(l => l > 0));
      const uncoveredSet = new Set(
        this.coveredLines.filter(l => l < 0).map(l => -l));

      if (coveredSet.has(lineNum)) {
        return ">     1 :";
      }
      if (uncoveredSet.has(lineNum)) {
        return "        0 :";
      }
      return "         :";
    },
    getLineDataClass(lineNum) {
      const coveredSet = new Set(
        this.coveredLines.filter(l => l > 0));
      const uncoveredSet = new Set(
        this.coveredLines.filter(l => l < 0).map(l => -l));

      if (coveredSet.has(lineNum)) {
        return "line-data-covered";
      }
      if (uncoveredSet.has(lineNum)) {
        return "line-data-uncovered";
      }
      return "";
    },
    getLineSourceClass(lineNum) {
      const coveredSet = new Set(
        this.coveredLines.filter(l => l > 0));
      const uncoveredSet = new Set(
        this.coveredLines.filter(l => l < 0).map(l => -l));

      if (coveredSet.has(lineNum)) {
        return "line-source-covered";
      }
      if (uncoveredSet.has(lineNum)) {
        return "line-source-uncovered";
      }
      return "";
    },
    escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    },
    calculateFunctionCoverage(sourceContent, coveredLines) {
      if (!sourceContent || !coveredLines) {
        return { total: 0, hit: 0, rate: 0 };
      }

      const lines = sourceContent.split("\n");
      const coveredSet = new Set(coveredLines.map(l => Number(l)));
      const functions = [];
      let inFunction = false;
      let functionStartLine = 0;
      let braceCount = 0;

      // Simple function detection for C/C++ code
      const staticInlineExtern = "(?:static|inline|extern)";
      const funcDef = "\\w+\\s*\\([^)]*\\)\\s*\\{?\\s*$";
      const patternStr =
        `^\\s*(?:${staticInlineExtern}\\s+)?(?:\\w+\\s+)*${funcDef}`;
      const functionPattern = new RegExp(patternStr);

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        if (functionPattern.test(trimmed) && !inFunction) {
          inFunction = true;
          functionStartLine = i + 1;
          braceCount = (line.match(/\{/g) || []).length -
            (line.match(/\}/g) || []).length;
        } else if (inFunction) {
          braceCount += (line.match(/\{/g) || []).length -
            (line.match(/\}/g) || []).length;

          if (braceCount <= 0 && trimmed) {
            functions.push({
              start: functionStartLine,
              end: i + 1
            });
            inFunction = false;
            braceCount = 0;
          }
        }
      }

      if (inFunction) {
        functions.push({
          start: functionStartLine,
          end: lines.length
        });
      }

      let hitFunctions = 0;
      functions.forEach(func => {
        for (let line = func.start; line <= func.end; line++) {
          if (coveredSet.has(line)) {
            hitFunctions++;
            break;
          }
        }
      });

      const total = functions.length;
      const rate = total > 0 ? (hitFunctions / total) * 100 : 0;

      return {
        total,
        hit: hitFunctions,
        rate: Math.round(rate * 10) / 10
      };
    }
  }
};
</script>

<style lang="scss" scoped>
.editor {
  font-size: initial;
  line-height: initial;

  ::v-deep .CodeMirror-code > div:hover {
    background-color: lighten(grey, 42%);
  }
}

.file-path-display {
  display: flex;
  align-items: center;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

.file-path-text {
  color: var(--v-primary-base);
  font-weight: 500;
}

.breadcrumb-nav {
  display: flex;
  align-items: center;
  margin-right: 16px;
  font-size: 0.9em;
}

.breadcrumb-link {
  color: var(--v-primary-base);
  text-decoration: none;
  margin: 0 4px;
  
  &:hover {
    text-decoration: underline;
  }
}

.breadcrumb-current {
  color: inherit;
  font-weight: 500;
  cursor: default;
  
  &:hover {
    text-decoration: none;
  }
}

.breadcrumb-separator {
  margin: 0 2px;
  color: #666;
}

.coverage-summary-wrapper {
  border: thin solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  padding: 8px;
  background-color: white;
}

.coverage-summary-table {
  width: 100%;
  border: 0;
  border-collapse: collapse;
  cellpadding: 1;
  cellspacing: 0;

  .summary-header-item {
    width: 10%;
    padding: 4px 8px;
    font-weight: bold;
    text-align: right;
    white-space: nowrap;
  }

  .summary-header-value {
    width: 10%;
    padding: 4px 8px;
    white-space: nowrap;
  }

  .summary-header-cov {
    width: 5%;
    padding: 4px 8px;
    font-weight: bold;
    text-align: center;
    background-color: #f5f5f5;
    border-bottom: 1px solid rgba(0, 0, 0, 0.12);
  }

  .summary-label {
    width: 5%;
    text-align: right;
    padding: 4px 8px;
    font-weight: bold;
    white-space: nowrap;
  }

  .summary-spacer {
    width: 5%;
    padding: 4px;
  }

  .summary-cov-value {
    width: 5%;
    text-align: right;
    padding: 4px 8px;
    font-weight: bold;
    white-space: nowrap;
  }

  .summary-cov-number {
    width: 5%;
    text-align: right;
    padding: 4px 8px;
    white-space: nowrap;
  }

  .breadcrumb-inline {
    font-size: 0.9em;
  }

  .breadcrumb-link-inline {
    color: #0066cc;
    text-decoration: underline;
    cursor: pointer;
    
    &:hover {
      color: #004499;
    }
  }

  .breadcrumb-current-inline {
    color: #000;
    font-weight: normal;
  }

  .breadcrumb-separator-inline {
    margin: 0 4px;
    color: #666;
  }

  .breadcrumb-meta {
    font-size: 80%;
    color: #0066cc;
    margin-left: 4px;
    
    a {
      color: #0066cc;
      text-decoration: underline;
    }
  }

  .coverage-high {
    background-color: #a7fc9d;
    color: #000000;
  }

  .coverage-medium {
    background-color: #ffea20;
    color: #000000;
  }

  .coverage-low {
    background-color: #ff0000;
    color: #ffffff;
  }
}

.coverage-source-wrapper {
  border: thin solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  overflow-x: auto;
  font-family: monospace;
  background-color: white;
}

.source-heading {
  white-space: pre;
  font-weight: bold;
  margin: 0;
  padding: 4px 8px;
  background-color: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);

  .line-data-header {
    display: inline-block;
    width: 120px;
  }

  .source-code-header {
    display: inline-block;
  }
}

.source-content {
  white-space: pre;
  margin: 0;
  padding: 0;
  font-size: 13px;
  line-height: 1.5;

  .source-line {
    display: block;
    padding: 0 8px;

    &:hover {
      background-color: rgba(0, 0, 0, 0.02);
    }
  }

  .line-number {
    display: inline-block;
    width: 80px;
    text-align: right;
    padding-right: 8px;
    color: #666;
    user-select: none;
    background-color: #efe383;
  }

  .line-data {
    display: inline-block;
    width: 120px;
    text-align: right;
    padding-right: 8px;
    font-family: monospace;
    white-space: pre;
  }

  .line-data-covered {
    background-color: #CAD7FE; /* LCOV: tlaGNC style */
    color: #000000;
  }

  .line-data-uncovered {
    background-color: #FF6230; /* LCOV: tlaUNC style */
    color: #000000;
  }

  .line-source {
    display: inline-block;
    padding-left: 8px;
  }

  .line-source-covered {
    background-color: rgba(202, 215, 254, 0.3); /* Light blue-green */
  }

  .line-source-uncovered {
    background-color: rgba(255, 98, 48, 0.3); /* Orange-red */
  }
}

::v-deep .coverage-line-covered {
  /* Green for covered (GCOV: tlaGNC, tlaCBC style) */
  background-color: rgba(167, 252, 157, 0.7) !important;
}

::v-deep .coverage-line-uncovered {
  /* Red for uncovered executable (GCOV: tlaUNC style) */
  background-color: rgba(255, 98, 48, 0.7) !important;
}
</style>

