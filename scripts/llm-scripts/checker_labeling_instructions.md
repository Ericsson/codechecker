# CodeChecker SEI Cert mapping

## 1. TASK

We would like You to identify which SEI Rules that are corresponding to static analysis checkers.
Checkers are implemented by static analyzer tools such as gcc or clang-tidy.
There are multiple analyzer tools supported by CodeChecker.
There is a `config` directory in CodeChecker which contains metadata about the supported analyzers and checkers.
This metadata describes among other things the severity of the checkers, the profile of the checker, and any corresponding SEI-Cert-rule or other guideline rule. There might be checkers which do not have any corresponding sie-cert rule.

This metadata is not complete and the corresponding sei-cert rule might be missing.

Add the missing SEI Cert rule mapping to the CodeChecker label files based on the checker documentation, source code of the checker, Sei-cert test results and the SEI Cert rule description.

Check the existing label mappings and remove any that are not relevant.

Make sure that the correct severity labels are added for each checker according to the CodeChecker severity definitions.

## 2. INPUT
| Path | Contents |
|------|----------|
| `scripts/llm-scripts/cppcheck` | The source code and documentation of cppcheck analyzer and checkers |
| `scripts/llm-scripts/gcc` | The source code and the documentation of the gcc static analyzer and checkers |
| `scripts/llm-scripts/sei-cert-rules` | Sei Cert rule description |
| `scripts/llm-scripts/sei-cert-tests` | Sei-Cert test results. There are multiple test cases per each SEI Cert rule demonstrating violations of the rule. Each test case file is named after the corresponding rule. This folder contains a json file per analyzer with the output of the tested analyzer on the test files. If a checker of an analyzer has a relevant finding on a test case, there is likely a correspondence of the given checker and the SEI Cert rule. |
| `config/labels/descriptions.json` | CodeChecker label definitions including severity and guideline definitions.|

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
