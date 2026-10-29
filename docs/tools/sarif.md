# CodeChecker SARIF Format

`CodeChecker parse <report_dir> --export sarif` converts the analyzer result
files (`.plist`) of a report directory into a single
[SARIF v2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
file. Nothing from the result files is lost. CodeChecker-specific data is
stored in the standard SARIF extension points (`partialFingerprints` and
property bags), so generic SARIF consumers such as GitHub code scanning and the
VS Code SARIF viewer can still read the file.

The same layout is used by `report-converter --export sarif`, and the SARIF
parser of CodeChecker reads it back without loss.

## Table of Contents
* [Runs](#runs)
* [Field mapping](#field-mapping)
* [File paths](#file-paths)
* [Report hashes](#report-hashes)
* [Example](#example)

## Runs

The file contains a separate `run` for each analyzer (`clangsa`, `clang-tidy`,
`cppcheck`, `gcc`, ...), ordered by analyzer name. Each run contains:

- `tool.driver.name`: the analyzer name, taken from `metadata.analyzer.name`
  of the plist files. Reports without an analyzer go into a run named
  `unknown`.
- `tool.driver.rules`: the checkers of this analyzer which have reports.
- `tool.driver.properties.generatedBy`: the name and version of the tool that
  wrote the file (CodeChecker or report-converter).
- `artifacts`: the files the reports of this run refer to.
- `results`: the reports of this analyzer.

## Field mapping

| Report data (plist) | SARIF location |
|---|---|
| report hash (`issue_hash_content_of_line_in_context`) | `result.partialFingerprints["codeCheckerReportHash/v1"]` |
| analyzer (`metadata.analyzer.name`) | `run.tool.driver.name` |
| checker (`check_name`) | `result.ruleId`, `result.ruleIndex` |
| message (`description`) | `result.message.text` |
| severity | `result.level` and `result.properties.severity` |
| main location (`location`) | `result.locations[0].physicalLocation` |
| bug path events (`path`, kind `event`) | `result.codeFlows[0].threadFlows[0].locations[]` with `message` and `importance: "important"` |
| bug path positions/arrows (`path`, kind `control`) | `result.codeFlows[0].threadFlows[1]` with `properties: {"codeChecker.kind": "bugPathPositions"}`, locations without message |
| notes (`notes`) | `result.relatedLocations[]` with `properties: {"codeChecker.kind": "note"}` |
| macro expansions (`macro_expansions`) | `result.relatedLocations[]` with `message.text` = expansion and `properties: {"codeChecker.kind": "macroExpansion", "name": <macro name>}` |
| `category`, `type` | `result.properties.category`, `result.properties.type` |
| report annotations (`report-annotation`) | `result.properties.annotations` |
| review status | `result.suppressions[]` |

If the line and column of an event, note or macro expansion differ from the
start of its range, they are stored in
`location.properties["codeChecker.position"] = {"line": ..., "column": ...}`.
An event without range has a region without `endLine`/`endColumn`.

## File paths

Absolute paths are written as percent-encoded `file://` URIs (e.g.
`file:///home/user/my%20project/main.c`). Paths that became relative through
`--trim-path-prefix` are written as relative references with
`uriBaseId: "SRCROOT"`; `originalUriBaseIds` is intentionally omitted, so the
absolute prefix is not revealed. Every `artifactLocation` also has an `index`
into `run.artifacts`.

## Report hashes

The report hash is copied verbatim from the analyzer result file and is never
recomputed. When CodeChecker parses a SARIF file, it uses the
`codeCheckerReportHash/v1` fingerprint if present, and computes a hash only
for SARIF files from other tools.

## Example

One clangsa report and one clang-tidy report. The hash values are
placeholders.

```json
{
  "version": "2.1.0",
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "clang-tidy",
          "rules": [
            {
              "id": "bugprone-use-after-move",
              "fullDescription": { "text": "'buf' used after it was moved" },
              "helpUri": "https://clang.llvm.org/extra/clang-tidy/checks/bugprone/use-after-move.html",
              "defaultConfiguration": { "level": "error" }
            }
          ],
          "properties": {
            "generatedBy": { "name": "CodeChecker", "version": "6.28.0" }
          }
        }
      },
      "artifacts": [
        { "location": { "uri": "file:///home/user/project/src/util.cpp" } }
      ],
      "results": [
        {
          "ruleId": "bugprone-use-after-move",
          "ruleIndex": 0,
          "level": "error",
          "message": { "text": "'buf' used after it was moved" },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": { "uri": "file:///home/user/project/src/util.cpp", "index": 0 },
                "region": { "startLine": 18, "startColumn": 3, "endLine": 18, "endColumn": 3 }
              }
            }
          ],
          "partialFingerprints": {
            "codeCheckerReportHash/v1": "8d1a6c3f0b2e4a7d9c5f1e3b2a4d6c8e"
          },
          "codeFlows": [
            {
              "threadFlows": [
                {
                  "locations": [
                    {
                      "location": {
                        "physicalLocation": {
                          "artifactLocation": { "uri": "file:///home/user/project/src/util.cpp", "index": 0 },
                          "region": { "startLine": 18, "startColumn": 3, "endLine": 18, "endColumn": 3 }
                        },
                        "message": { "text": "'buf' used after it was moved" }
                      },
                      "importance": "important"
                    }
                  ]
                }
              ]
            }
          ],
          "relatedLocations": [
            {
              "id": 0,
              "message": { "text": "move occurred here" },
              "physicalLocation": {
                "artifactLocation": { "uri": "file:///home/user/project/src/util.cpp", "index": 0 },
                "region": { "startLine": 16, "startColumn": 9, "endLine": 16, "endColumn": 9 }
              },
              "properties": { "codeChecker.kind": "note" }
            }
          ],
          "properties": {
            "severity": "HIGH",
            "category": "unknown",
            "type": "clang-tidy"
          }
        }
      ]
    },
    {
      "tool": {
        "driver": {
          "name": "clangsa",
          "rules": [
            {
              "id": "core.NullDereference",
              "fullDescription": { "text": "Dereference of null pointer (loaded from variable 'p')" },
              "helpUri": "https://clang.llvm.org/docs/analyzer/checkers.html#core-nulldereference-c-c-objc",
              "defaultConfiguration": { "level": "error" }
            }
          ],
          "properties": {
            "generatedBy": { "name": "CodeChecker", "version": "6.28.0" }
          }
        }
      },
      "artifacts": [
        { "location": { "uri": "file:///home/user/project/src/main.c" } }
      ],
      "results": [
        {
          "ruleId": "core.NullDereference",
          "ruleIndex": 0,
          "level": "error",
          "message": { "text": "Dereference of null pointer (loaded from variable 'p')" },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                "region": { "startLine": 12, "startColumn": 6, "endLine": 12, "endColumn": 6 }
              }
            }
          ],
          "partialFingerprints": {
            "codeCheckerReportHash/v1": "3f7c2b9e1d4a5f6b8c0e2d4f6a8b0c1d"
          },
          "codeFlows": [
            {
              "threadFlows": [
                {
                  "locations": [
                    {
                      "location": {
                        "physicalLocation": {
                          "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                          "region": { "startLine": 10, "startColumn": 3, "endLine": 10, "endColumn": 14 }
                        },
                        "message": { "text": "'p' initialized to a null pointer value" }
                      },
                      "importance": "important"
                    },
                    {
                      "location": {
                        "physicalLocation": {
                          "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                          "region": { "startLine": 12, "startColumn": 6, "endLine": 12, "endColumn": 6 }
                        },
                        "message": { "text": "Dereference of null pointer (loaded from variable 'p')" }
                      },
                      "importance": "important"
                    }
                  ]
                },
                {
                  "properties": { "codeChecker.kind": "bugPathPositions" },
                  "locations": [
                    {
                      "location": {
                        "physicalLocation": {
                          "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                          "region": { "startLine": 10, "startColumn": 3, "endLine": 10, "endColumn": 5 }
                        }
                      }
                    },
                    {
                      "location": {
                        "physicalLocation": {
                          "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                          "region": { "startLine": 12, "startColumn": 3, "endLine": 12, "endColumn": 8 }
                        }
                      }
                    }
                  ]
                }
              ]
            }
          ],
          "relatedLocations": [
            {
              "id": 0,
              "message": { "text": "((void *)0)" },
              "physicalLocation": {
                "artifactLocation": { "uri": "file:///home/user/project/src/main.c", "index": 0 },
                "region": { "startLine": 10, "startColumn": 12, "endLine": 10, "endColumn": 12 }
              },
              "properties": { "codeChecker.kind": "macroExpansion", "name": "NULL" }
            }
          ],
          "properties": {
            "severity": "HIGH",
            "category": "Logic error",
            "type": "clangsa"
          }
        }
      ]
    }
  ]
}
```
