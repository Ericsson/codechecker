# CodeChecker Labeling

## TASKS

In this section different tasks are defined to update checker labels in CodeChecker.
To complete a task use only those input sources which are listed as relevant in the "Used in Task" column of the table in section INPUT.

### sei-cert-mapping
We would like You to identify which SEI Rules that are corresponding to static analysis checkers.
Checkers are implemented by static analyzer tools such as gcc or clang-tidy.
There are multiple analyzer tools supported by CodeChecker.
There is a [config](https://github.com/Ericsson/codechecker/tree/master/config/labels/analyzers) directory in CodeChecker which contains metadata about the supported analyzers and checkers.
This metadata describes among other things the severity of the checkers, the profile of the checker, and any corresponding SEI-Cert-rule or other guideline rule. There might be checkers which do not have any corresponding sie-cert rule.

This metadata is not complete and the corresponding sei-cert rule might be missing.

Add the missing SEI Cert rule mapping to the CodeChecker label files based on the checker documentation, source code of the checker, Sei-cert test results and the SEI Cert rule description.

Check the existing label mappings and remove any that are not relevant.

### severity-mapping
Make sure that the correct severity labels are added for each checker according to the CodeChecker severity definitions.

### profile-mapping
Classify the checkers into CodeChecker profiles based on evaluation results.

Noisiness is measured relative to the **median report count** across all checkers
in the evaluation data.

* default-profile: Checkers with LOW, MEDIUM or HIGH severity whose report count
  is ≤ 30× the median. Alpha, experimental, style, and debug checkers are excluded. Also exclude rules which are targeting a specific non-linux platform or programming library such as: abseil, boost, fuchsia, google, llvm, zircon.

* sensitive-profile: Checkers with LOW, MEDIUM or HIGH severity whose report count
  is > 30× and ≤ 100× the median. Alpha, experimental, style, and debug checkers are excluded. Also exclude rules which are targeting a specific non-linux platform or programming library such as: abseil, boost, fuchsia, google, llvm, zircon.

* Checkers with report count > 100× the median are considered "very noisy" and are
  excluded from both profiles unless explicitly overridden.


## 2. INPUT
| Path | Contents |Used in Task|
|------|----------|------------|
| `scripts/llm-scripts/cppcheck` | The source code and documentation of cppcheck analyzer and checkers |all tasks|
| `scripts/llm-scripts/gcc` | The source code and the documentation of the gcc static analyzer and checkers |all tasks|
| `scripts/llm-scripts/clang-tidy-checks` | The source code of the clang-tidy static analyzer and checkers |all tasks|
| `scripts/llm-scripts/clang-tidy-docs` | The documentation of the clang-tidy static analyzer and checkers |all tasks|
| `scripts/llm-scripts/clangsa-checks` | The source code of the clang static analyzer and checkers |all tasks|
| `scripts/llm-scripts/clangsa-docs` | The source code of the clang static analyzer and checkers |all tasks|
| `scripts/llm-scripts/clang-warning-docs` | Clang warnings documentation |all tasks|
| `scripts/llm-scripts/sei-cert-rules` | Sei Cert rule description |sei-cert-mapping|
| `scripts/llm-scripts/sei-cert-tests` | Sei-Cert test results. There are multiple test cases per each SEI Cert rule demonstrating violations of the rule. Each test case file is named after the corresponding rule. This folder contains a json file per analyzer with the output of the tested analyzer on the test files. If a checker of an analyzer has a relevant finding on a test case, there is likely a correspondence of the given checker and the SEI Cert rule. | sei-cert-mapping|
| `config/labels/descriptions.json` | CodeChecker label definitions including severity and guideline definitions.|all tasks|
| `scripts/llm-scripts/evaluation-results`| Analysis results on open source projects| profile-mapping|


## 3. OUTPUT

| Path | Contents |
|------|----------|
| `config/labels/analyzers` | CodeChecker label files in json format |

## 4. CRITICAL RULES

1. Do not add any sei-cert rule labels where you are not sure about the correspondence.
2. If you are unsure in the correspondence then always ask the user. do not guess.
3. Never make up any sei-cert rule id. Only use existing rule ids.
4. Always follow this naming convention of the labels sei-cert-c:<rule id> for example: sei-cert-c:mem34-c

## 5. ROLES

- **You (AI Agent):** enterprise-level security expert assisting with the audit.
- **User:** application-level Product Owner / Architect for CodeChecker.

## 6. Evaluation order of INPUT SOURCES
When finding a corresponding SEI-cert rule for a checker take into consideration the input sources in the following order of decreasing priority.

1. The source code of the checker
2. The documentation of the checker
3. The test result of the checker for the given SEI Cert test case
