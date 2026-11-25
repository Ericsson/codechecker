
# Configuration

## Rules

Rules are the main building blocks of the configuration, each rule file containing all the rules defined by the owner of them. Any given rule have an ID, a title and an url. Every rule can be added to one or more groups called Guidelines.

Rule descriptors can be found under `rules/*`.

## Guidelines

Guidelines are collection of rules which are compiled based on different criteria. The descriptor of a given guideline contains its id, a title, an URL and all the connected rules.

The descriptors can be found under `guidelines/*`.

## Labels

Labels are descriptors of a checker. Each checker have one which describes various properties of it like the documentation URL, the severity, what profile or guideline it belongs to or what rules are connected to it. Each label files are tied to a given analyzer which all of the listed checkers belong to.

The label descriptors can be found under `labels/analyzers/*`.

Current labels are:

| Label | Description |
| ------- | ------------- |
| doc_url | The URL of the checker documentation |
| profile | A grouping of checker that can be used after `--enable`/`--disable` flags during analysis. |
| rule | A given rule assigned to the checker. It can be rules from CWE, SEI-CERT, OWASP, etc. |
| severity | Indicates how severe a bug described by the given checker is when it occurs. |

This space contains also the descriptions file which mainly contains the descriptions for profiles and severities along with the profile containment.

### Profile

In CodeChecker profiles can be sorted into 2 categories:

- **Cumulative profiles (Default, Sensitive, Extreme):** As the name suggests, each of these profiles enables progressively more checkers. Default enabled the fewest, making the results the least noisy but it might hide potential issues whilst Extreme enables all, surfacing the most potential issues but making the results noisy at the same time.
- **Thematic profiles (Security, Portability):** Unlike the nested profiles, thematic profiles are not ordered by sensitivity. Instead, each one groups together the checkers relevant to a specific concern.

### Rule

Rules are assigned to a checker by the `rule:` label. A checker can have several rules from multiple guidelines. A rule assigned to a checker will define not just the rule itself but the guidelines too. E.g. assigning the rule `cwe-123` to a checker will make it show up in the guidelines which groups CWE rules together in the guideline statistics.

### Severity

As for severities, the following levels are defined:

- **STYLE**: A true positive indicates that the source code is against a specific coding guideline or could improve readability.
Example: LLVM Coding Guideline: Do not use else or else if after something that interrupts control flow (break, return, throw, continue).

- **LOW**: A true positive indicates that the source code is hard to read/understand or could be easily optimized.
Example: Unused variables, Dead code.

- **MEDIUM**: A true positive indicates that the source code that may not cause a run-time error (yet), but against intuition and hence prone to error.
Example: Redundant expression in a condition.

- **HIGH**: A true positive indicates that the source code will cause a run-time error.
  Example of this category: out of bounds array access, division by zero, memory leak.

- **CRITICAL**: Currently used for indicating compilation errors.

- **UNSPECIFIED**: Checker severity is not specified for a checker.

## Default configuration

- Environment Variables (config.json): Contains enviroment variable names set and used during the static analysis
- Checker Config (config_files/codechecker.yml/.json): This file contains the default configuration for CodeChecker like the default enabled checkers for the analyzer or the default workspace and port for the server.

## Session configuration

  * authentication section
    Contains configuration for a **server** on how to handle authentication
  * credentials section
    Contains the **client** user's preconfigured authentication tokens.
  * tokens section
    Contains session tokens the **client** user has received through authentication. This section is **not** meant to be configured by hand.

## gdb script

Contains an automated gdb script which can be used for debug. In debug mode the failed build commands will be rerun with gdb.

## version

Version file contains version information for the package
