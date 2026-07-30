<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card class="elevation-0">
          <v-card-title class="text-h5 font-weight-bold">
            Code Coverage Report
            <v-spacer />
            <v-progress-circular
              v-if="loading"
              indeterminate
              size="24"
              color="primary"
              class="ml-2"
            />
          </v-card-title>

          <v-divider />

          <!-- Header Statistics Section -->
          <v-card-text>
            <v-row class="mb-4">
              <v-col cols="12">
                <v-simple-table dense class="coverage-header-table">
                  <tbody>
                    <tr>
                      <td class="header-item">
                        Current view:
                      </td>
                      <td class="header-value">
                        <span v-if="breadcrumbs.length > 1">
                          <router-link
                            v-for="(crumb, idx) in breadcrumbs"
                            :key="idx"
                            :to="crumb.to"
                            class="breadcrumb-link"
                          >
                            {{ crumb.text }}
                            <span v-if="idx < breadcrumbs.length - 1"> - </span>
                          </router-link>
                        </span>
                        <span v-else>top level</span>
                      </td>
                      <td />
                      <td class="header-item">
                        Coverage
                      </td>
                      <td class="header-item">
                        Total
                      </td>
                      <td class="header-item">
                        Hit
                      </td>
                    </tr>
                    <tr>
                      <td class="header-item">
                        Test:
                      </td>
                      <td class="header-value">
                        coverage.info
                      </td>
                      <td />
                      <td class="header-item">
                        Lines:
                      </td>
                      <td 
                        :class="getCoverageClass(displayLinesCoverage)"
                        class="header-cov-entry"
                      >
                        {{ displayLinesCoverage }}&nbsp;%
                      </td>
                      <td class="header-cov-entry">
                        {{ displayLinesTotal }}
                      </td>
                      <td class="header-cov-entry">
                        {{ displayLinesHit }}
                      </td>
                    </tr>
                    <tr>
                      <td class="header-item">
                        Test Date:
                      </td>
                      <td class="header-value">
                        {{ displayTestDate }}
                      </td>
                      <td />
                      <td class="header-item">
                        Functions:
                      </td>
                      <td 
                        :class="getCoverageClass(displayFunctionsCoverage)"
                        class="header-cov-entry"
                      >
                        {{ displayFunctionsCoverage }}&nbsp;%
                      </td>
                      <td class="header-cov-entry">
                        {{ displayFunctionsTotal }}
                      </td>
                      <td class="header-cov-entry">
                        {{ displayFunctionsHit }}
                      </td>
                    </tr>
                  </tbody>
                </v-simple-table>
              </v-col>
            </v-row>

            <v-divider class="mb-4" />

            <!-- Breadcrumb Navigation -->
            <v-row v-if="breadcrumbs.length > 0" class="mb-2">
              <v-col cols="12">
                <v-breadcrumbs :items="breadcrumbs" class="pa-0">
                  <template v-slot:divider>
                    <v-icon>mdi-chevron-right</v-icon>
                  </template>
                  <template v-slot:item="{ item }">
                    <v-breadcrumbs-item
                      :to="item.to"
                      :disabled="item.disabled"
                      class="breadcrumb-item"
                    >
                      {{ item.text }}
                    </v-breadcrumbs-item>
                  </template>
                </v-breadcrumbs>
              </v-col>
            </v-row>

            <!-- File Search -->
            <v-row class="mb-2">
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="searchQuery"
                  prepend-inner-icon="mdi-magnify"
                  label="Filter by file or directory name"
                  clearable
                  dense
                  outlined
                  hide-details
                />
              </v-col>
            </v-row>

            <!-- Main Coverage Table -->
            <v-row>
              <v-col cols="12">
                <div class="coverage-table-wrapper">
                  <table class="coverage-statistics-table">
                    <thead>
                      <tr>
                        <th rowspan="2" class="table-head directory-header">
                          {{ isFileView ? "File" : "Directory" }}
                        </th>
                        <th colspan="4" class="table-head">
                          Line Coverage
                        </th>
                        <th colspan="3" class="table-head">
                          Function Coverage
                        </th>
                      </tr>
                      <tr>
                        <th class="table-head sub-header" colspan="2">
                          Rate
                        </th>
                        <th class="table-head sub-header">
                          Total
                        </th>
                        <th class="table-head sub-header">
                          Hit
                        </th>
                        <th class="table-head sub-header">
                          Rate
                        </th>
                        <th class="table-head sub-header">
                          Total
                        </th>
                        <th class="table-head sub-header">
                          Hit
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(item, index) in filteredCoverageItems"
                        :key="index"
                        class="coverage-row"
                      >
                        <td class="directory-cell">
                          <router-link
                            v-if="item.link"
                            :to="item.link"
                            class="directory-link"
                          >
                            <v-icon
                              v-if="!item.isFile"
                              small
                              class="mr-1"
                            >
                              mdi-folder
                            </v-icon>
                            <v-icon
                              v-else
                              small
                              class="mr-1"
                            >
                              mdi-file-code
                            </v-icon>
                            {{ item.name }}
                          </router-link>
                          <span v-else>
                            <v-icon
                              v-if="!item.isFile"
                              small
                              class="mr-1"
                            >
                              mdi-folder
                            </v-icon>
                            <v-icon
                              v-else
                              small
                              class="mr-1"
                            >
                              mdi-file-code
                            </v-icon>
                            {{ item.name }}
                          </span>
                        </td>
                        <td class="coverage-bar-cell">
                          <div class="coverage-bar-container">
                            <div class="coverage-bar">
                              <div 
                                class="coverage-bar-filled"
                                :class="getCoverageBarClass(item.lineRate)"
                                :style="{ width: item.lineRate + '%' }"
                              />
                              <div 
                                class="coverage-bar-empty"
                                :style="{ width: (100 - item.lineRate) + '%' }"
                              />
                            </div>
                          </div>
                        </td>
                        <td 
                          :class="getCoverageClass(item.lineRate)"
                          class="coverage-percentage-cell"
                        >
                          {{ item.lineRate }}&nbsp;%
                        </td>
                        <td class="coverage-number-cell">
                          {{ item.lineTotal }}
                        </td>
                        <td class="coverage-number-cell">
                          {{ item.lineHit }}
                        </td>
                        <td 
                          :class="getCoverageClass(item.functionRate)"
                          class="coverage-percentage-cell"
                        >
                          {{ item.functionRate }}&nbsp;%
                        </td>
                        <td class="coverage-number-cell">
                          {{ item.functionTotal }}
                        </td>
                        <td class="coverage-number-cell">
                          {{ item.functionHit }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </v-col>
            </v-row>

            <v-divider class="mt-4" />

            <v-row class="mt-2">
              <v-col cols="12" class="text-center">
                <span class="version-info">
                  Generated by:
                  <a href="https://github.com/Ericsson/codechecker">
                    CodeChecker
                  </a>
                </span>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ccService, handleThriftError } from "@cc-api";
import { BaseStatistics } from "@/components/Statistics";

export default {
  name: "CoverageStatistics",
  mixins: [ BaseStatistics ],
  props: {
    bus: { type: Object, required: true },
    namespace: { type: String, required: true }
  },
  data() {
    return {
      loading: false,
      searchQuery: "",
      fetchedCoverageData: [],
      fetchedSummary: null,
      allFileData: [],
      currentPath: "",
      fileDataMap: new Map()
    };
  },
  computed: {
    currentViewPath() {
      if (!this.currentPath) {
        return "top level";
      }
      return this.currentPath === "/" ? "/" : this.currentPath;
    },
    breadcrumbs() {
      const crumbs = [
        {
          text: "top level",
          to: { name: "code-coverage-statistics" },
          disabled: !this.currentPath
        }
      ];

      if (this.currentPath) {
        const parts = this.currentPath.split("/").filter(p => p);
        let path = "";
        parts.forEach((part, index) => {
          path += (path ? "/" : "") + part;
          crumbs.push({
            text: part,
            to: {
              name: "code-coverage-statistics",
              query: { path: path }
            },
            disabled: index === parts.length - 1
          });
        });
      }

      return crumbs;
    },
    isFileView() {
      // Check if we're viewing files (when currentPath matches a dir)
      if (!this.currentPath) {
        return false;
      }
      // If currentPath matches a directory that has files, show files
      return this.coverageItems.some(item => item.isFile);
    },
    coverageItems() {
      if (!this.currentPath) {
        // Top level: show top-level directories
        return this.getTopLevelDirectories();
      }

      // Get items for current path
      return this.getItemsForPath(this.currentPath);
    },
    filteredCoverageItems() {
      if (!this.searchQuery) {
        return this.coverageItems;
      }
      const q = this.searchQuery.toLowerCase();
      return this.coverageItems.filter(item =>
        item.name.toLowerCase().includes(q));
    },
    displayTestDate() {
      if (this.fetchedSummary && this.fetchedSummary.testDate) {
        return this.fetchedSummary.testDate;
      }
      return new Date().toLocaleString();
    },
    displayLinesCoverage() {
      if (this.fetchedSummary &&
          this.fetchedSummary.linesCoverage !== undefined) {
        return this.fetchedSummary.linesCoverage;
      }
      return 0;
    },
    displayLinesTotal() {
      if (this.fetchedSummary &&
          this.fetchedSummary.linesTotal !== undefined) {
        return this.fetchedSummary.linesTotal;
      }
      return 0;
    },
    displayLinesHit() {
      if (this.fetchedSummary &&
          this.fetchedSummary.linesHit !== undefined) {
        return this.fetchedSummary.linesHit;
      }
      return 0;
    },
    displayFunctionsCoverage() {
      if (this.fetchedSummary &&
          this.fetchedSummary.functionsCoverage !== undefined) {
        return this.fetchedSummary.functionsCoverage;
      }
      return 0;
    },
    displayFunctionsTotal() {
      if (this.fetchedSummary &&
          this.fetchedSummary.functionsTotal !== undefined) {
        return this.fetchedSummary.functionsTotal;
      }
      return 0;
    },
    displayFunctionsHit() {
      if (this.fetchedSummary &&
          this.fetchedSummary.functionsHit !== undefined) {
        return this.fetchedSummary.functionsHit;
      }
      return 0;
    }
  },
  watch: {
    "$route.query.path"(newPath) {
      this.currentPath = newPath || "";
    }
  },
  activated() {
    this.bus.$on("refresh", this.fetchStatistics);
  },
  deactivated() {
    this.bus.$off("refresh", this.fetchStatistics);
  },
  mounted() {
    this.fetchStatistics();
    this.updateCurrentPathFromQuery();
  },
  methods: {
    async fetchStatistics() {
      this.loading = true;
      this.fetchedCoverageData = [];
      this.fetchedSummary = null;

      try {
        const client = ccService.getClient();

        if (typeof client.getFilesWithCoverage !== "function") {
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

        if (!files || files.length === 0) {
          this.loading = false;
          this.fetchedSummary = {
            testDate: new Date().toLocaleString(),
            linesCoverage: 0, linesTotal: 0, linesHit: 0,
            functionsCoverage: 0, functionsTotal: 0, functionsHit: 0
          };
          return;
        }

        // fileContent carries "hit/total", remoteUrl carries "fnf/fnh"
        const validCoverageData = files.map(file => {
          let lineHit = 0;
          let lineTotal = 0;
          if (file.fileContent) {
            const lp = file.fileContent.split("/");
            lineHit = parseInt(lp[0], 10) || 0;
            lineTotal = parseInt(lp[1], 10) || lineHit;
          }
          let fnFound = 0;
          let fnHit = 0;
          if (file.remoteUrl) {
            const parts = file.remoteUrl.split("/");
            fnFound = parseInt(parts[0], 10) || 0;
            fnHit = parseInt(parts[1], 10) || 0;
          }
          const dir = file.filePath.substring(
            0, file.filePath.lastIndexOf("/")) || "/";
          return {
            fileId: file.fileId,
            filePath: file.filePath,
            directory: dir,
            lineHit,
            lineTotal,
            lineRate: lineTotal > 0
              ? Math.round((lineHit / lineTotal) * 1000) / 10 : 0,
            functionTotal: fnFound,
            functionHit: fnHit,
            functionRate: fnFound > 0
              ? Math.round((fnHit / fnFound) * 1000) / 10 : 0
          };
        });

        // Group by directory
        const directoryMap = new Map();

        validCoverageData.forEach(fileData => {
          const dir = fileData.directory;
          if (!directoryMap.has(dir)) {
            directoryMap.set(dir, {
              directory: dir + (dir !== "/" ? "/" : ""),
              lineRate: 0, lineTotal: 0, lineHit: 0,
              functionRate: 0, functionTotal: 0, functionHit: 0,
              fileCount: 0, files: []
            });
          }

          const dirData = directoryMap.get(dir);
          dirData.lineTotal += fileData.lineTotal;
          dirData.lineHit += fileData.lineHit;
          dirData.functionTotal += fileData.functionTotal;
          dirData.functionHit += fileData.functionHit;
          dirData.fileCount += 1;
          dirData.files.push({
            fileId: fileData.fileId,
            filePath: fileData.filePath
          });
        });

        // Calculate rates for each directory and set links
        directoryMap.forEach(dirData => {
          dirData.lineRate = dirData.lineTotal > 0
            ? Math.round((dirData.lineHit / dirData.lineTotal) * 1000) / 10
            : 0;
          dirData.functionRate = dirData.functionTotal > 0
            ? Math.round(
              (dirData.functionHit / dirData.functionTotal) * 1000) / 10
            : 0;
          // Set directory link to first file in directory
          if (dirData.files.length > 0) {
            const firstFile = dirData.files[0];
            dirData.directoryLink = {
              name: "code-coverage-statistics",
              query: {
                fileId: firstFile.fileId.toString(),
                filePath: firstFile.filePath
              }
            };
          } else {
            dirData.directoryLink = {
              name: "code-coverage-statistics"
            };
          }
        });

        this.fetchedCoverageData = Array.from(directoryMap.values());
        this.allFileData = validCoverageData;

        // Build file data map for quick lookup
        this.fileDataMap.clear();
        validCoverageData.forEach(fileData => {
          this.fileDataMap.set(fileData.filePath, fileData);
        });

        // Summary from aggregated data
        const totalHit = validCoverageData.reduce(
          (s, d) => s + d.lineHit, 0);
        const totalLines = validCoverageData.reduce(
          (s, d) => s + d.lineTotal, 0);
        const totalFnFound = validCoverageData.reduce(
          (s, d) => s + d.functionTotal, 0);
        const totalFnHit = validCoverageData.reduce(
          (s, d) => s + d.functionHit, 0);

        this.fetchedSummary = {
          testDate: new Date().toLocaleString(),
          linesCoverage: totalLines > 0
            ? Math.round((totalHit / totalLines) * 1000) / 10 : 0,
          linesTotal: totalLines,
          linesHit: totalHit,
          functionsCoverage: totalFnFound > 0
            ? Math.round((totalFnHit / totalFnFound) * 1000) / 10 : 0,
          functionsTotal: totalFnFound,
          functionsHit: totalFnHit
        };
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Could not load coverage data:", error);
        // Set empty data to show the UI properly
        this.fetchedCoverageData = [];
        this.fetchedSummary = {
          testDate: new Date().toLocaleString(),
          linesCoverage: 0,
          linesTotal: 0,
          linesHit: 0,
          functionsCoverage: 0,
          functionsTotal: 0,
          functionsHit: 0
        };
      } finally {
        this.loading = false;
      }
    },
    getCoverageClass(coverage) {
      // GCOV logic: High >= 80%, Medium 50-79%, Low < 50%
      if (coverage >= 80) {
        return "coverage-high";
      } else if (coverage >= 50) {
        return "coverage-medium";
      } else {
        return "coverage-low";
      }
    },
    getCoverageBarClass(coverage) {
      if (coverage >= 80) {
        return "coverage-bar-high";
      } else if (coverage >= 50) {
        return "coverage-bar-medium";
      } else {
        return "coverage-bar-low";
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
      // Look for function definitions (not perfect but reasonable)
      const staticInlineExtern = "(?:static|inline|extern)";
      const funcDef = "\\w+\\s*\\([^)]*\\)\\s*\\{?\\s*$";
      const patternStr =
        `^\\s*(?:${staticInlineExtern}\\s+)?(?:\\w+\\s+)*${funcDef}`;
      const functionPattern = new RegExp(patternStr);

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Check if this looks like a function definition
        if (functionPattern.test(trimmed) && !inFunction) {
          inFunction = true;
          functionStartLine = i + 1;
          braceCount = (line.match(/\{/g) || []).length -
            (line.match(/\}/g) || []).length;
        } else if (inFunction) {
          braceCount += (line.match(/\{/g) || []).length -
            (line.match(/\}/g) || []).length;

          if (braceCount <= 0 && trimmed) {
            // Function ended
            functions.push({
              start: functionStartLine,
              end: i + 1
            });
            inFunction = false;
            braceCount = 0;
          }
        }
      }

      // If we're still in a function at the end, close it
      if (inFunction) {
        functions.push({
          start: functionStartLine,
          end: lines.length
        });
      }

      // Check which functions have at least one covered line
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
    },
    updateCurrentPathFromQuery() {
      this.currentPath = this.$route.query.path || "";
    },
    getBasePath() {
      // Find the common base path from all file paths
      if (!this.fetchedCoverageData || this.fetchedCoverageData.length === 0) {
        return "";
      }

      // Normalize paths (remove trailing slashes for comparison)
      const paths = this.fetchedCoverageData.map(data => {
        const dir = data.directory;
        return dir.endsWith("/") ? dir.slice(0, -1) : dir;
      });

      if (paths.length === 0) {
        return "";
      }

      if (paths.length === 1) {
        // If only one path, check if it's a root path
        const path = paths[0];
        if (path === "" || path === "/") {
          return "";
        }
        // Return parent directory
        const lastSlash = path.lastIndexOf("/");
        return lastSlash > 0 ? path.substring(0, lastSlash) : "";
      }

      // Find the longest common prefix
      let commonPrefix = paths[0];
      for (let i = 1; i < paths.length; i++) {
        const path = paths[i];
        let j = 0;
        const minLength = Math.min(commonPrefix.length, path.length);
        while (j < minLength && commonPrefix[j] === path[j]) {
          j++;
        }
        commonPrefix = commonPrefix.substring(0, j);

        // If no common prefix, return empty
        if (commonPrefix === "" || commonPrefix === "/") {
          return "";
        }
      }

      // Find the last directory separator to get a valid directory path
      // This ensures we return a complete directory path, not a partial one
      const lastSlash = commonPrefix.lastIndexOf("/");
      if (lastSlash > 0) {
        return commonPrefix.substring(0, lastSlash);
      } else if (lastSlash === 0 && commonPrefix.length > 1) {
        // Path starts with / but has more content
        return "";
      }

      return "";
    },
    getTopLevelDirectories() {
      if (!this.fetchedCoverageData || this.fetchedCoverageData.length === 0) {
        return [];
      }

      // Get unique top-level directories
      const topLevelDirs = new Map();
      
      this.fetchedCoverageData.forEach(dirData => {
        // Normalize directory path
        let path = dirData.directory;
        if (path.endsWith("/") && path !== "/") {
          path = path.slice(0, -1);
        }
        
        // Handle absolute paths - extract just the last directory component
        // For paths like "/Users/.../GCOV" or "GCOV", we want "GCOV"
        const pathParts = path.split("/").filter(p => p && p !== "");
        const topLevelName = pathParts.length > 0
          ? pathParts[pathParts.length - 1]
          : "";
        
        if (!topLevelName) {
          // If path is empty or just "/", skip it
          return;
        }
        
        // Full path for the top level directory (always start with /)
        // Ensure it ends with / for consistency
        const topLevelFullPath = `/${topLevelName}/`;
        
        if (!topLevelDirs.has(topLevelFullPath)) {
          topLevelDirs.set(topLevelFullPath, {
            name: topLevelName,
            directory: topLevelFullPath,
            lineRate: 0,
            lineTotal: 0,
            lineHit: 0,
            functionRate: 0,
            functionTotal: 0,
            functionHit: 0,
            isFile: false,
            link: {
              name: "code-coverage-statistics",
              query: { path: topLevelFullPath }
            }
          });
        }

        const topDir = topLevelDirs.get(topLevelFullPath);
        topDir.lineTotal += dirData.lineTotal;
        topDir.lineHit += dirData.lineHit;
        topDir.functionTotal += dirData.functionTotal;
        topDir.functionHit += dirData.functionHit;
      });

      // Calculate rates
      topLevelDirs.forEach(dirData => {
        dirData.lineRate = dirData.lineTotal > 0
          ? Math.round((dirData.lineHit / dirData.lineTotal) * 1000) / 10
          : 0;
        dirData.functionRate = dirData.functionTotal > 0
          ? Math.round(
            (dirData.functionHit / dirData.functionTotal) * 1000) / 10
          : 0;
      });

      return Array.from(topLevelDirs.values())
        .sort((a, b) => a.name.localeCompare(b.name));
    },
    getItemsForPath(path) {
      // Normalize the path - ensure it starts with / and ends with /
      let normalizedPath = path || "";
      if (!normalizedPath.startsWith("/")) {
        normalizedPath = "/" + normalizedPath;
      }
      if (!normalizedPath.endsWith("/")) {
        normalizedPath = normalizedPath + "/";
      }
      
      // Find all directories and files that match this path
      const subdirs = new Map();
      const files = [];

      // Check fetchedCoverageData for matching directories
      this.fetchedCoverageData.forEach(dirData => {
        // Normalize directory path
        let dirPath = dirData.directory;
        if (!dirPath.endsWith("/") && dirPath !== "/") {
          dirPath = dirPath + "/";
        }
        if (!dirPath.startsWith("/")) {
          dirPath = "/" + dirPath;
        }
        
        // Extract the last N components from dirPath to match normalizedPath
        // normalizedPath is like "/GCOV/" (relative, top-level)
        // dirPath might be "/Users/.../GCOV/" (absolute)
        // Check if the last component(s) of dirPath match normalizedPath
        
        const dirPathParts = dirPath.split("/").filter(p => p && p !== "");
        const normalizedPathParts = normalizedPath.split("/")
          .filter(p => p && p !== "");
        
        // Check if the last N parts of dirPath match normalizedPath
        if (dirPathParts.length < normalizedPathParts.length) {
          return; // Skip if dirPath is shorter than what we're looking for
        }
        
        // Get the last N parts of dirPath
        const dirPathSuffix = dirPathParts
          .slice(-normalizedPathParts.length)
          .join("/");
        const normalizedPathStr = normalizedPathParts.join("/");
        
        // Check if the suffix matches
        if (dirPathSuffix !== normalizedPathStr) {
          return; // Skip if doesn't match
        }
        
        // Calculate relative path depth
        // When suffix matches, check if we're at the exact directory level
        // (last component matches) or if there are subdirectories
        const depthDiff = dirPathParts.length - normalizedPathParts.length;
        
        // Check if the last component of dirPath matches the last component 
        // of normalizedPath (exact directory match)
        const isExactDirectory = dirPathParts.length > 0 &&
          normalizedPathParts.length > 0 &&
          dirPathParts[dirPathParts.length - 1] === 
          normalizedPathParts[normalizedPathParts.length - 1];
        
        if (isExactDirectory && depthDiff === 0) {
          // This is the exact directory (same depth), check for files
          if (dirData.files && dirData.files.length > 0) {
            dirData.files.forEach(file => {
              const fileData = this.fileDataMap.get(file.filePath);
              if (fileData) {
                files.push({
                  name: file.filePath.split("/").pop(),
                  directory: fileData.directory,
                  lineRate: fileData.lineRate,
                  lineTotal: fileData.lineTotal,
                  lineHit: fileData.lineHit,
                  functionRate: fileData.functionRate,
                  functionTotal: fileData.functionTotal,
                  functionHit: fileData.functionHit,
                  isFile: true,
                  fileId: fileData.fileId,
                  filePath: fileData.filePath,
                  link: {
                    name: "code-coverage-file",
                    params: this.$route.params,
                    query: {
                      fileId: fileData.fileId.toString(),
                      filePath: fileData.filePath
                    }
                  }
                });
              }
            });
          }
        } else if (isExactDirectory && depthDiff > 0) {
          // Absolute path matches relative path's last component
          // We're viewing this directory, show its files
          if (dirData.files && dirData.files.length > 0) {
            dirData.files.forEach(file => {
              const fileData = this.fileDataMap.get(file.filePath);
              if (fileData) {
                files.push({
                  name: file.filePath.split("/").pop(),
                  directory: fileData.directory,
                  lineRate: fileData.lineRate,
                  lineTotal: fileData.lineTotal,
                  lineHit: fileData.lineHit,
                  functionRate: fileData.functionRate,
                  functionTotal: fileData.functionTotal,
                  functionHit: fileData.functionHit,
                  isFile: true,
                  fileId: fileData.fileId,
                  filePath: fileData.filePath,
                  link: {
                    name: "code-coverage-file",
                    params: this.$route.params,
                    query: {
                      fileId: fileData.fileId.toString(),
                      filePath: fileData.filePath
                    }
                  }
                });
              }
            });
          }
        } else if (depthDiff > 0) {
          // There's a subdirectory - get the next level
          const subdirName = dirPathParts[dirPathParts.length - depthDiff];
          const subdirFullPath = `${normalizedPath}${subdirName}/`
            .replace(/\/+/g, "/");
          
          if (!subdirs.has(subdirFullPath)) {
            subdirs.set(subdirFullPath, {
              name: subdirName,
              directory: subdirFullPath,
              lineRate: 0,
              lineTotal: 0,
              lineHit: 0,
              functionRate: 0,
              functionTotal: 0,
              functionHit: 0,
              isFile: false,
              link: {
                name: "code-coverage-statistics",
                query: { path: subdirFullPath }
              }
            });
          }

          const subdir = subdirs.get(subdirFullPath);
          subdir.lineTotal += dirData.lineTotal;
          subdir.lineHit += dirData.lineHit;
          subdir.functionTotal += dirData.functionTotal;
          subdir.functionHit += dirData.functionHit;
        }
      });

      // Calculate rates for subdirectories
      subdirs.forEach(dirData => {
        dirData.lineRate = dirData.lineTotal > 0
          ? Math.round((dirData.lineHit / dirData.lineTotal) * 1000) / 10
          : 0;
        dirData.functionRate = dirData.functionTotal > 0
          ? Math.round(
            (dirData.functionHit / dirData.functionTotal) * 1000) / 10
          : 0;
      });

      // Combine subdirectories and files, sort them
      // Priority: Show files first (like GCOV), then subdirectories
      const sortedSubdirs = Array.from(subdirs.values())
        .sort((a, b) => a.name.localeCompare(b.name));
      const sortedFiles = files.sort((a, b) => a.name.localeCompare(b.name));
      
      // If we have files, show them first
      // (GCOV behavior: directory view shows files)
      // If no files but subdirectories, show subdirectories
      if (sortedFiles.length > 0) {
        return sortedFiles;
      }
      return sortedSubdirs;
    }
  }
};
</script>

<style lang="scss" scoped>
.coverage-header-table {
  border: thin solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;

  .header-item {
    text-align: right;
    padding-right: 6px;
    font-weight: bold;
    white-space: nowrap;
    vertical-align: top;
    color: var(--v-grey-darken2);
  }

  .header-value {
    text-align: left;
    color: var(--v-primary-base);
    font-weight: bold;
    white-space: nowrap;

    .breadcrumb-link {
      color: var(--v-primary-base);
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .header-cov-entry {
    text-align: right;
    padding-left: 12px;
    padding-right: 4px;
    font-weight: bold;
    white-space: nowrap;
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
    color: #000000;
  }
}

.coverage-table-wrapper {
  overflow-x: auto;
  border: thin solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}

.coverage-statistics-table {
  width: 100%;
  border-collapse: collapse;
  background-color: white;

  .table-head {
    background-color: var(--v-primary-base);
    color: white;
    font-weight: bold;
    text-align: center;
    padding: 12px 8px;
    border: 1px solid rgba(255, 255, 255, 0.2);

    &.directory-header {
      text-align: left;
    }

    &.sub-header {
      font-size: 0.9em;
      font-weight: normal;
    }
  }

  .coverage-row {
    &:nth-child(even) {
      background-color: #f5f5f5;
    }

    &:hover {
      background-color: rgba(0, 0, 0, 0.04);
    }
  }

  td {
    padding: 8px;
    border: 1px solid rgba(0, 0, 0, 0.12);
  }

  .directory-cell {
    background-color: #b8d0ff;
    font-family: monospace;
  }

  .directory-link {
    color: var(--v-primary-base);
    text-decoration: none;
    font-weight: normal;

    &:hover {
      text-decoration: underline;
    }
  }

  .coverage-bar-cell {
    padding: 8px;
    text-align: center;
  }

  .coverage-bar-container {
    display: flex;
    justify-content: center;
    padding: 4px 0;
  }

  .coverage-bar {
    display: flex;
    width: 100%;
    max-width: 150px;
    height: 20px;
    border: 1px solid #000000;
    border-radius: 2px;
    overflow: hidden;
  }

  .coverage-bar-filled {
    height: 100%;
    transition: width 0.3s ease;
  }

  .coverage-bar-high {
    background-color: #a7fc9d;
  }

  .coverage-bar-medium {
    background-color: #ffea20;
  }

  .coverage-bar-low {
    background-color: #ff0000;
  }

  .coverage-bar-empty {
    height: 100%;
    background-color: #ffffff;
  }

  .coverage-percentage-cell {
    text-align: right;
    font-weight: bold;
    padding: 8px 12px;
    white-space: nowrap;
  }

  .coverage-number-cell {
    text-align: right;
    padding: 8px 12px;
    white-space: nowrap;
    background-color: #dae7fe;
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
    color: #000000;
  }
}

.version-info {
  font-style: italic;
  font-size: 0.9em;
  color: var(--v-grey-darken1);

  a {
    color: var(--v-primary-base);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>

