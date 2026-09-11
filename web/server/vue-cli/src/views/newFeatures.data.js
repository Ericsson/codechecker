/* eslint-disable max-len */
// =============================================================================
// New features page content
// =============================================================================
//
// This file lists the CodeChecker releases shown on the "New features" page.
// You do NOT need to know Vue to edit it — you only fill in strings.
//
// HOW TO ADD A RELEASE
// --------------------
// Copy an existing release block and paste it at the TOP of the `releases`
// array below, then edit the fields. The FIRST release in the array is always
// treated as the latest: it is expanded and highlighted automatically. You do
// not set any colors by hand.
//
// A release looks like this:
//
//   {
//     version: "6.30.0",
//     url: "https://github.com/Ericsson/codechecker/releases/tag/v6.30.0",
//     features: [ ...list of features... ]
//   }
//
// A feature looks like this:
//
//   {
//     title: "Short feature name",
//
//     // OPTIONAL. Set to true if this feature is a backward-incompatible
//     // change. The feature header then shows a red "Backward incompatible
//     // changes!" alert together with the feature name. Omit it otherwise.
//     breaking: true,
//
//     // The description is a list of "blocks" shown in the given order.
//     // Each block has a `type` and a `value`. Supported types:
//     //
//     //   { type: "text",  value: "<p>HTML text: <code>code</code>, " +
//     //                            "<a href='...'>links</a>, lists, etc.</p>" }
//     //   { type: "code",  value: "multi-line code / CLI example" }
//     //   { type: "image", value: "file-name.png" }
//     //
//     // Images are looked up automatically under:
//     //   src/assets/userguide/images/new_features/<version>/<file-name>
//     // (their alt text defaults to the feature title).
//     blocks: [
//       { type: "text", value: "..." }
//     ]
//   }
//
// =============================================================================

export default [
  {
    version: "6.29.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.29.0",
    features: [
      {
        title: "Redesigned file tree view",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The report file tree view has been redesigned. You can filter
                paths by wildcard, sort them by severity or review status, pick
                paths with checkboxes, and the tree auto-expands to the first
                branching folder.
              </p>
              <p>
                The current view mode and expanded folders are now captured in
                the URL, so shared links will show the exact same view.
              </p>
            `
          },
          { type: "image", value: "report_tree.png" }
        ]
      },
      {
        title: "GCC compiler warnings as checkers",
        blocks: [
          {
            type: "text",
            value: `
              Any <code>-W</code> GCC warning can now be enabled and reported
              like a standard checker.
            `
          }
        ]
      },
      {
        title: "OWASP Top 10 (2025) and CWE vulnerabilities guidelines",
        blocks: [
          {
            type: "text",
            value: `
              New security guidelines with rule and CWE mappings are added,
              shown directly in the guideline statistics.
            `
          },
          { type: "image", value: "guideline_statistics.png" }
        ]
      },
      {
        title: "Richer SARIF export from parse",
        blocks: [
          {
            type: "text",
            value: `
              The SARIF output of the <code>CodeChecker parse</code> command now
              includes suppression information and complete rule details, and
              includes all review statuses by default, improving CI and
              third-party tool integration.
            `
          }
        ]
      },
      {
        title:
          "Analysis configuration stored with the run and visible in the GUI",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The skip file and other configuration files are now kept
                alongside the run and shown in the redesigned analysis
                information dialog, giving a clear record of exactly how a run
                was analyzed.
              </p>
            `
          },
          { type: "image", value: "skipfile_analysis_info.png" }
        ]
      },
      {
        title: "Redesigned report info page",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The report info page has been redesigned to present all details
                of a report in clearly organized cards: run and report
                information, analyzer and checker details, file and location,
                bug path length and severity, detection and review status, and
                detection and fix dates.
              </p>
              <p>
                Values such as the run name, report hash, file path, checker and
                analyzer name link directly to the matching filtered reports
                view.
              </p>
            `
          },
          { type: "image", value: "report_info.png" }
        ]
      },
      {
        title: "More readable report steps",
        blocks: [
          {
            type: "text",
            value: `
              Lengthy step messages now wrap across multiple lines, and step
              boxes are color-coded by type (error, fixit, macro, note).
            `
          }
        ]
      },
      {
        title: "Improved statistics pages",
        blocks: [
          {
            type: "text",
            value: `
              A refined layout, a single-select guideline picker, more readable
              colors, and checkers missing from the selected runs are shown as
              disabled rather than blocking the view from loading.
            `
          }
        ]
      },
      {
        title: "New memory-safety reporting tool",
        blocks: [
          {
            type: "text",
            value: `
              A helper script combines a run's findings, checker details, and
              analyzer configuration into a single, checksummed archive.
            `
          }
        ]
      },
      {
        title: "Faster, cleaner command-line output",
        blocks: [
          {
            type: "text",
            value: `
              Human-readable output uses terminal-width-aware tables, analyzers
              are scheduled so longer-running ones start earlier, and the CLI
              can now be invoked as lowercase <code>codechecker</code>.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.28.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.28.0",
    features: [
      {
        title: "Upgrade CodeChecker to use Vue 3",
        blocks: [
          {
            type: "text",
            value: "<p>CodeChecker GUI is now rewritten to the Vue 3 framework.</p>"
          },
          { type: "image", value: "vue3.png" }
        ]
      },
      {
        title: "Addition of Saving and Loading of Filter Presets",
        blocks: [
          {
            type: "text",
            value: `
              Frequently used report filters can be saved into named "presets"
              and later can be reloaded.
            `
          },
          { type: "image", value: "filter-preset.png" },
          {
            type: "text",
            value: `
              The filter presets can also be accessed in the CLI with the
              <code>CodeChecker cmd filter-preset</code> commands.
            `
          }
        ]
      },
      {
        title: "List enabled checkers in CLI",
        blocks: [
          {
            type: "text",
            value: `
              You can list the enabled checkers for any runs from the CLI by
              executing:
            `
          },
          { type: "code", value: "CodeChecker cmd runs -n <RUN_NAME> -o json" }
        ]
      },
      {
        title: "Adding Checker coverage statistics to CLI",
        blocks: [
          {
            type: "text",
            value: `
              The
              <code>CodeChecker cmd sum -n tinxyml_sensitive &lt;run_name&gt;</code>
              command lists the checkers that have findings and any
              corresponding guideline rules.
            `
          }
        ]
      },
      {
        title:
          "Extend SEI Cert guideline mapping for cppcheck and gcc analyzers",
        blocks: [
          {
            type: "text",
            value: `
              All supported
              <a href="https://gcc.gnu.org/onlinedocs/gcc/Static-Analyzer-Options.html" target="_blank">gcc static analyzer</a>
              and
              <a href="https://cppcheck.sourceforge.io/" target="_blank">cppcheck</a>
              checkers now have the SEI Cert rule associations.
            `
          }
        ]
      },
      {
        title: "Enable passing credentials from environment variable",
        blocks: [
          {
            type: "text",
            value: `
              The authentication credentials can now be passed from an
              environment variable besides the
              <code>.codechecker_password.json</code> file.
            `
          },
          {
            type: "code",
            value: `export CC_PASSWORD="secret"
CodeChecker cmd login username`
          }
        ]
      },
      {
        title: "Add PMD analyzer support",
        blocks: [
          {
            type: "text",
            value: `
              It is now possible to store the analysis results of the
              <a href="https://pmd.github.io/" target="_blank">PMD analyzer</a>.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.27.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.27.0",
    features: [
      {
        title: "Asynchronous Store",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                CodeChecker changes its store execution model from synchronous
                to asynchronous mode.
              </p>
              <p>
                The <code>CodeChecker store</code> command will not have to wait
                synchronously for the server to finish the storage procedure of
                the reports, but can seamlessly continue execution after the
                store process started. Then later, it can query the status of
                the storage task from the server.
              </p>
              <p>
                This provides more stable report storage procedures as many
                users experienced broken TCP connections during large analysis
                results storage batches.
              </p>
              <p>
                CodeChecker will provide a command line utility for admins to
                query ongoing/finished/cancelled storage processes with
                filtering options.
              </p>
            `
          },
          {
            type: "code",
            value: `❯ build/CodeChecker/bin/CodeChecker cmd serverside-tasks --enqueued-after 2024:08:19 --status cancelled
Token                                                            | Machine            | Type                   | Summary                         | Status    | Product | User | Enqueued            | Started             | Last seen           | Completed           | Cancelled?
8b62497c7d1b7e3945445f5b9c3951d97ae07e58f97cad60a0187221e7d1e2ba | xxxxxxxxxxxxx:8001 | taskService::DummyTask | Dummy task for testing purposes | CANCELLED |         |      | 2024-08-19 15:55:34 | 2024-08-19 15:55:34 | 2024-08-19 15:55:35 | 2024-08-19 15:55:35 | Yes
6fa0097a9bd1799572c7ccd2afc0272684ed036c11145da7eaf40cc8a07c7241 | xxxxxxxxxxxxx:8001 | taskService::DummyTask | Dummy task for testing purposes | CANCELLED |         |      | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | 2024-08-19 15:55:53 | Yes`
          }
        ]
      },
      {
        title: "Detailed analysis status command",
        blocks: [
          {
            type: "code",
            value:
              "CodeChecker parse --status ./report_dir [--detailed] [-e json]"
          },
          {
            type: "text",
            value: `
              <p>
                This command provides a clear overview of the current state of
                analysis results within the report directory, indicating which
                reports are up to date, which are outdated, which analyses have
                failed, and which files were never processed (e.g. skipped).
              </p>
              <p>Example output:</p>
            `
          },
          {
            type: "code",
            value: `----==== Summary ====----
Up-to-date analysis results
  clangsa: 311
  clang-tidy: 311
Outdated analysis results
Failed to analyze
  clangsa: 20
  clang-tidy: 20
Missing analysis results
  clangsa: 18
  clang-tidy: 18
  cppcheck: 349
Total analyzed compilation commands: 331
Total available compilation commands: 349
----=================----`
          },
          {
            type: "text",
            value: `
              <p>
                The <code>--detailed</code> flag shows the exact files involved
                instead of just counts. For automated workflows, the
                <code>-e json</code> option provides the status info in a format
                that can be easily processed.
              </p>
            `
          }
        ]
      },
      {
        title: "New Component Filter mode: single-origin-report",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                A new report filter option is introduced to CodeChecker:
                Single Origin mode. This option makes it possible to filter only
                those reports which are contained entirely within a source code
                component. To use it, select the "Single Origin" mode when
                editing the Source Component filter in the Reports view.
              </p>
              <p>
                This new option is also available from the command line using
                the <code>--single-origin-report</code> argument.
                E.g:
                <code>CodeChecker cmd results --single-origin-report --component my_component ...</code>
              </p>
            `
          },
          { type: "image", value: "single-origin.png" }
        ]
      },
      {
        title: "Highlight non-compliant guideline rules",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Non-compliant rules are highlighted in the SEI-Cert statistics
                and compliant rules can be hidden.
              </p>
            `
          },
          { type: "image", value: "non-compliant.png" }
        ]
      },
      {
        title: "Navigable numbers in the product statistics page",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The values of the outstanding reports graph are now clickable.
              </p>
            `
          },
          { type: "image", value: "navigable-numbers.png" }
        ]
      }
    ]
  },
  {
    version: "6.26.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.26.0",
    features: [
      {
        title: "OAuth2 based Single Sign On Authentication",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                CodeChecker now provides OAuth2 based user authentication
                through various providers. It is now possible to configure your
                CodeChecker server instance to accept user logins with their
                Google, Microsoft or GitHub accounts.
              </p>
              <p>
                To enable this feature, you will first need to configure your
                CodeChecker server instance with the corresponding OAuth
                provider and add a new authentication method section in the
                CodeChecker server configuration file.
              </p>
              <p>
                If the user group memberships are managed by a Microsoft Entra
                identity server, these memberships will be fetched by
                CodeChecker through the graph API.
              </p>
              <p>
                See the
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/web/authentication.md#oauth-authentication-" target="_blank">CodeChecker authentication document</a>
                for configuration details.
              </p>
            `
          },
          { type: "image", value: "oauth.png" }
        ]
      },
      {
        title: "Personal Access Token Management",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Personal access tokens are generated "passwords" which can be
                used to login to CodeChecker. If Multi-Factor Authentication is
                enabled, it is the only way to authenticate through the CLI.
              </p>
              <ul>
                <li>
                  The Personal Access Tokens now can be created on the GUI too,
                  not only through the CLI.
                </li>
                <li>
                  It is accessible if you click on your username in the top
                  right corner.
                </li>
              </ul>
            `
          },
          { type: "image", value: "personal_access_token.png" }
        ]
      },
      {
        title: "Personal Access Tokens cannot be viewed after creation",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The Personal Access Tokens cannot be viewed after creation. It
                used to be possible to list the values of the personal access
                tokens after creation, but after this version it will only be
                possible to view them once at creation time.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.25.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.25.0",
    features: [
      {
        title:
          "Guideline Statistics page to generate SEI Cert Compliance reports",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                A new Guideline Statistics page was added under the Statistics
                tab to generate SEI Cert Compliance reports.
              </p>
            `
          },
          { type: "image", value: "guideline_statistics.png" },
          {
            type: "text",
            value: `
              <p>
                This page shows the compliance of an analyzed program to a
                coding guideline (such as SEI Cert C/C++). It shows all checkers
                corresponding to a guideline rule, their configuration status
                (on/off) and all outstanding and closed reports per guideline
                rule.
              </p>
              <p>
                It is possible to generate the table into HTML and CSV format.
              </p>
              <p>The first supported guidelines are SEI Cert C and C++.</p>
            `
          }
        ]
      },
      {
        title: "Facebook Infer as a new C/C++ analyzer plugin",
        blocks: [
          {
            type: "text",
            value: `
              Besides clang-tidy, clang static analyzer, cppcheck and gcc,
              <a href="https://github.com/facebook/infer" target="_blank">Facebook Infer</a>
              is a well known open-source static code analyzer tool.
              CodeChecker will support executing this analyzer. It will not be
              enabled by default, but is available for testing.
            `
          },
          { type: "image", value: "infer.png" }
        ]
      },
      {
        title: "PVS Studio report conversion",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                From now on, it will be possible to convert the reports of the
                <a href="https://pvs-studio.com/en/pvs-studio/" target="_blank">PVS Studio</a>
                analyzer and handle them with CodeChecker.
              </p>
            `
          }
        ]
      },
      {
        title: "Checker enable/disable, skip file and guideline changes",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <p><b>Checker enable/disable ambiguity resolved</b></p>
              <p>
                CodeChecker analyze emits an error (instead of a warning) when
                the enabled checkers/profiles/checker prefix groups are given
                ambiguously. In these cases the ambiguity must be resolved. For
                example <code>CodeChecker analyze -e security command</code> is
                ambiguous as <code>security</code> is a checker group (all
                checkers starting with <code>security</code>), and a profile at
                the same time. Please define explicitly
                <code>CodeChecker -e prefix:security</code> if you mean the
                prefix group, or <code>profile:security</code> if you mean the
                security profile.
              </p>
              <p>
                <code>CodeChecker -e clang-diagnostic-format</code> will give an
                error, because it is ambiguous if the user means the
                <code>clang-diagnostic-format</code> single checker, or all
                checkers starting with <code>clang-diagnostic-format</code>. To
                refer to the former, the user must use
                <code>checker:clang-diagnostic-format</code> or to the latter
                <code>prefix:clang-diagnostic-format</code>.
              </p>
              <p>
                If you have such clashing cases, you must resolve them. The
                following namespaces can be used:
                <br>
                <code>prefix:</code> - to match checkers starting with a prefix
                <br>
                <code>profile:</code> - to match a checker profile
                <br>
                <code>checker:</code> - to match a single checker
                <br>
                <code>guideline:</code> - to match checkers belonging to a
                guideline
                <br>
                <code>severity:</code> - to match checkers belonging to a given
                severity
              </p>
              <p><b>The skip file handling was changed</b></p>
              <p>
                The <code>--drop-reports-from-skipped-files</code> parameter was
                added to analyze. After this change, the skip files will only
                skip the analysis of the listed files, but will not filter out
                any reports. This may result in more reports than before.<br>
                By default CodeChecker used to filter out all reports from files
                which were on the skip list. This can hide true positive reports
                starting from unskipped code and ending in skipped files
                (typical with CTU and header related findings). This patch
                removes the default report filtering post processing step from
                <code>CodeChecker analyze --skip SKIPFILE</code> operation. The
                legacy functionality is still available with the
                <code>--drop-reports-from-skipped-files</code> parameter.
              </p>
              <p><b><code>guideline:sei-cert</code> cannot be used anymore</b></p>
              <p>
                The sei-cert guideline profile was split to
                <code>guideline:sei-cert-c</code> for the C guideline and
                <code>guideline:sei-cert-cpp</code> for the C++ guideline.
              </p>
              <p>
                <b><code>CodeChecker -e W*</code> syntax is not supported
                anymore</b>
              </p>
              <p>
                Clang warnings only appear as <code>clang-diagnostic-*</code>
                checkers and they can be enabled using the standard checker
                on/off mechanism e.g.
                <code>CodeChecker analyze -e clang-diagnostic-unused-function</code>
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.24.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.24.0",
    features: [
      {
        title: "Listing of Enabled/Disabled Checkers in the WEB UI per run",
        blocks: [
          {
            type: "text",
            value: `
              CodeChecker provides a new view in the "Analysis information tab"
              which lists all checkers that were enabled during analysis.
            `
          }
        ]
      },
      {
        title:
          "New Checker Coverage Statistics view with coding guideline references",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                CodeChecker provides a new view to display all enabled checkers
                for a set of selected runs. Additionally, it also lists all
                guideline rules related to the given checker. For example, you
                can verify whether your code has any SEI Cert coding guideline
                violation.
              </p>
              <p>
                The new table lists all checkers that were enabled in a set of
                selected analysis runs, shows the number of outstanding reports
                and the number of closed reports per enabled checker and the
                related coding guideline rules.
              </p>
            `
          }
        ]
      },
      {
        title: "Faster run storage",
        blocks: [
          {
            type: "text",
            value: `
              Thanks to a new optimization, the run storage duration can be up
              to 50% faster.
            `
          }
        ]
      },
      {
        title: "New Static HTML Report Pages",
        blocks: [
          {
            type: "text",
            value: `
              The static HTML generation is rewritten so it can handle much
              larger result sets.
            `
          }
        ]
      },
      {
        title: "New report filter to list closed and outstanding reports",
        blocks: [
          {
            type: "text",
            value: `
              A new filter has been added to list outstanding and closed
              reports. An outstanding report is a report with detection status
              new, reopened, unresolved with review status unreviewed or
              confirmed.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.23.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.23.0",
    features: [
      {
        title: "GCC Static Analyzer support",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We are happy to announce that CodeChecker added native support
                for the
                <a href="https://gcc.gnu.org/wiki/StaticAnalyzer" target="_blank">GCC Static Analyzer</a>!
                This analyzer checks code in the C family of languages, but its
                latest release at the time of writing is still best used only on
                C code. Despite it being a bit immature for C++, we did some
                internal surveys where the GCC Static Analyzer seemed to be
                promising.
              </p>
              <p>
                We expect this analyzer to be slower than clang-tidy, but faster
                than the Clang Static Analyzer. You can enable it by adding
                <code>--analyzers gcc</code> to your
                <code>CodeChecker check</code> or
                <code>CodeChecker analyze</code> commands. For further
                configuration, check out the
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/checker_and_analyzer_configuration.md#gcc-static-analyzer" target="_blank">GCC Static Analyzer configuration page</a>.
              </p>
              <p>
                GNU GCC 13.0.0. (the minimum version we support) can be tricky
                to obtain and to make CodeChecker use it, as CodeChecker looks
                for the <code>g++</code> binary, not <code>g++-13</code>. As a
                workaround, you can set the environmental variable
                <code>CC_ANALYZER_BIN</code> which will make CodeChecker use the
                given analyzer path (e.g.
                <code>CC_ANALYZER_BIN="gcc:/usr/bin/g++-13"</code>). You can use
                <code>CodeChecker analyzers</code> to check whether you have the
                correct binary configured.
              </p>
              <p>
                You can enable gcc checkers by explicitly mentioning them at the
                analyze command e.g.
              </p>
            `
          },
          { type: "code", value: "CodeChecker analyze -e gcc" },
          {
            type: "text",
            value: `
              <p>
                gcc checkers are only added to the extreme profile. After
                evaluation, some checkers may be added to other profiles too.
              </p>
              <p>
                Under the same breath, we added partial support for the
                <a href="https://sarifweb.azurewebsites.net/" target="_blank">SARIF</a>
                file format (as opposed to using plists) to
                <code>report-converter</code>, with greater support planned for
                future releases.
              </p>
            `
          }
        ]
      },
      {
        title: "Review status config file",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                In previous CodeChecker versions, you could set the review
                status of a report using two methods: using
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/user_guide.md#setting-with-source-code-comments" target="_blank">in-source comments</a>,
                or setting a
                <a href="https://github.com/Ericsson/codechecker/blob/master/web/server/vue-cli/src/assets/userguide/userguide.md#review-status" target="_blank">review status rule</a>
                in the GUI. The former sets the specific report's review status,
                the latter sets all matching reports' review status.
              </p>
              <p>
                This release introduces a third way, a review status config
                file! One of the motivations behind this is that we wanted to
                have a way to set review statuses on reports in specific
                directories (which was not possible on the GUI). CodeChecker
                uses a YAML config file that can be set during analysis:
              </p>
            `
          },
          {
            type: "code",
            value: `$version: 1
rules:
  - filters:
      filepath: /path/to/project/test/*
      checker_name: core.DivideZero
    actions:
      review_status: intentional
      reason: Division by zero in test files is automatically intentional.

  - filters:
      filepath: /path/to/project/important/module/*
    actions:
      review_status: confirmed
      reason: All reports in this module should be investigated.

  - filters:
      filepath: "*/project/test/*"
    actions:
      review_status: suppress
      reason: If a filter starts with asterix, then it should be quoted due to YAML format.

  - filters:
      report_hash: b85851b34789e35c6acfa1a4aaf65382
    actions:
      review_status: false_positive
      reason: This report is false positive.`
          },
          {
            type: "text",
            value: "<p>This is how you can use this config file for an analysis:</p>"
          },
          {
            type: "code",
            value:
              "CodeChecker analyze compile_commands.json --review-status-config review_status.yaml -o reports"
          },
          {
            type: "text",
            value: `
              <p>
                The config file allows for a great variety of ways to match a
                report and set its review status. For further details see
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/user_guide.md#setting-with-config-file" target="_blank">this documentation</a>.
              </p>
            `
          }
        ]
      },
      {
        title: "Enable/disable status of checkers",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                <strong>
                  In this release the unknown Checker status has been
                  eliminated. CodeChecker will enable only those checkers that
                  are either present in the default profile (see CodeChecker
                  checkers --profile default) or enabled using the --enable
                  argument (through another profile or explicitly through a
                  checker name).
                </strong>
              </p>
              <p>
                In previous CodeChecker versions, when you ran an analysis, we
                assigned three states to every checker: it's either enabled,
                disabled, or neither (unknown). We kept the third state around to
                give some leeway for the analyzers to decide which checkers to
                enable or disable, usually to manage their checker dependencies.
                We now see that this behavior can be (and usually is) confusing,
                partly because it's hard to tell which checkers were actually
                enabled.
              </p>
              <p>
                You can list the checkers enabled by default using the
                CodeChecker checkers command:
              </p>
            `
          },
          {
            type: "code",
            value: `CodeChecker 6.22.0 output:

CodeChecker checkers |grep clang-diagnostic-varargs -A7
clang-diagnostic-varargs
  Status: unknown
  Analyzer: clang-tidy
  Description:
  Labels:
    doc_url:https://clang.llvm.org/docs/DiagnosticsReference.html#wvarargs
    severity:MEDIUM

=>
CodeChecker 6.23.0 output:

CodeChecker checkers |grep clang-diagnostic-varargs -A7
clang-diagnostic-varargs
  Status: disabled
  Analyzer: clang-tidy
  Description:
  Labels:
    doc_url:https://clang.llvm.org/docs/DiagnosticsReference.html#wvarargs
    severity:MEDIUM`
          }
        ]
      },
      {
        title: "Major fixes to run/tag comparisons (diff)",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Following a thorough survey, we identified numerous areas to
                improve on our run/tag comparisons. We landed several patches to
                improve the results of diffs both on the CLI and the web GUI
                (which should be almost always identical). Despite that this
                feature has the appearance of a simple set operation, diff is a
                powerful tool that can express a lot of properties on the state
                of your codebase, and has a few intricacies. For this reason, we
                also greatly improved
                <a href="https://github.com/Szelethus/codechecker/blob/diff_docs_rewrite/docs/web/diff.md" target="_blank">our docs</a>
                around it.
              </p>
              <p>
                A detailed description of the issues are described in this
                ticket:
                <a href="https://github.com/Ericsson/codechecker/issues/3884" target="_blank">#3884</a>
              </p>
              <p>
                One example is that if the suppression was removed for a
                finding, the diff did not show the reappearing result as new (in
                local/local diff):
              </p>
            `
          },
          {
            type: "code",
            value: `// Code version 1:
void c() {
  int i = 0; // deadstore, this value is never read
  // codechecker_suppress [all] SUPPRESS ALL
  i = 5;
}


// Code version 2 (suppression removed):

void c() {
  int i = 0; // deadstore, this value is never read
  i = 5;
}

CodeChecker diff -b version1.c -n version2.c --new
Did not show the deadstore finding as new.`
          }
        ]
      },
      {
        title: "Web GUI improvements",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We landed several patches to improve the readability and
                usability of the GUI, with more improvements to come in later
                releases! The currently selected event's visual highlight pops a
                little more now in the report view, and we no longer show unused
                columns in the run view.
              </p>
              <p>
                In the report detail page, outstanding and closed issues are
                clearly organized into a left tree view. So it will be easier to
                see which report needs more attention (fixing or triaging).
              </p>
            `
          }
        ]
      },
      {
        title: "Report limit for storing to the server",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Especially in the case of clang-tidy, we have observed some
                unreasonable number of reports by certain checkers. In some
                instances, we saw hundreds of thousands (!) of reports reported
                by some individual checkers, and it's more than unlikely that
                anyone will inspect these reports individually (you probably got
                the message about using parentheses around macros after the
                first 15 000 reports).
              </p>
              <p>
                We found that these checkers were usually enabled by mistake, and
                put unnecessary strain both on the storage of results to the
                server, and on the database once stored. Moving forward,
                CodeChecker servers will reject stores of runs that have more
                than 500 000 reports. This limit is a default value that you can
                change or even set to unlimited. Our intent is not to discourage
                legitimately huge stores, only those whose size is likely this
                large by mistake.
              </p>
              <p>
                When creating a new product called <code>My product</code> at
                endpoint <code>myproduct</code>, you can set the report limit
                from the CLI with the following invocation:
              </p>
            `
          },
          {
            type: "code",
            value:
              "CodeChecker cmd products add -n \"My product\" --report-limit 1000000 myproduct"
          },
          {
            type: "text",
            value: `
              <p>
                For an already existing product, you can change the limit by
                clicking the pencil at the products page.
              </p>
            `
          }
        ]
      },
      {
        title: "Promote the missing analyzer warning to an error",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <p>
                [analyzer] Promote the missing analyzer warning to an error
                <a href="https://github.com/Ericsson/codechecker/pull/3997" target="_blank">#3997</a>
              </p>
              <ul>
                <li>
                  If analyzers are specified with <code>--analyzers</code> flag
                  and one of them is missing, CodeChecker now emits an error.
                </li>
                <li>
                  Previously, the user could only specify the analyzers without
                  version number e.g.:
                  <code>CodeChecker analyze compile_commands.json -o reports --analyzers clangsa</code>
                </li>
                <li>
                  Now, you can also validate the analyzer's version number e.g.:
                  <code>CodeChecker analyze compile_commands.json -o reports --analyzers clangsa==14.0.0</code>
                </li>
                <li>
                  In both cases, if a wrong analyzer was given, the system exit
                  would trigger.
                </li>
              </ul>
              <p>
                <code>--all</code> and <code>--details</code> were deprecated for
                CodeChecker analyzers.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.22.2",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.22.2",
    features: [
      {
        title: "Support for Ubuntu 22.04",
        blocks: [
          {
            type: "text",
            value: `
              CodeChecker failed to build on Ubuntu 22.04 in its previous
              release because of two issues: some of our dependencies broke with
              the release of python3.9, and we didn't support GNU Make's new way
              of creating build jobs. These issues are all fixed now, so
              CodeChecker should work with the latest version of python and GNU
              Make!
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.22.1",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.22.1",
    features: [
      {
        title: "Bugfix, related to CodeChecker server",
        blocks: [
          {
            type: "text",
            value: `
              CodeChecker webapp was crashing when using the component filter,
              which has been fixed in this release.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.22.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.22.0",
    features: [
      {
        title: "Further enhancements to speed up the store procedure",
        blocks: [
          {
            type: "text",
            value: `
              After another round of optimizations, CodeChecker store is ~2
              times faster than in v6.21.0. Combined with the previous release,
              storing may be as much as 4 times faster than v6.20.0, with larger
              result directories seeing a greater degree of improvement.
              <br>
              This should allow those that use CodeChecker in CI loops to see
              fewer timeouts due to long storages, or lower timeout thresholds
              significantly.
            `
          }
        ]
      },
      {
        title: "Multiroot analysis",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                CodeChecker now supports an analysis mode where for each source
                file, it tries to find the closest compile_commands.json file up
                in the directory hierarchy starting from the source file.
              </p>
              <p>
                If your project is structured such that multiple folders act as
                their own root folder (hence the name multiroot), CodeChecker
                should be able to support that out of the box. clangd and
                clang-tidy already work this way.
              </p>
              <p>
                This feature also affects the CodeChecker Visual Studio Code
                plugin, where analysis will be done on multiroot projects as
                well.
              </p>
              <p>
                Previously the input of analysis must have been a compilation
                database JSON file. This PR supports the following new
                CodeChecker analyze invocations, as long as a corresponding
                compilation database file is found:
              </p>
            `
          },
          {
            type: "code",
            value: `# Analyze a single file.
CodeChecker analyze analyze.cpp -o reports

# Analyze all source files under a directory.
CodeChecker analyze my_project -o reports`
          }
        ]
      },
      {
        title:
          "Support report annotations and add dynamic analyzer related annotations",
        blocks: [
          {
            type: "text",
            value: `
              Unlike for static analyzers, the time of the detection can be a
              crucial piece of information, as a report may be a result of
              another preceding report. Users that record the timestamp of the
              detection and store it in CodeChecker under the new 'Timestamp'
              field will be able to sort reports by it. CodeChecker now also
              supports the 'Testsuite' field. You can read more about this
              feature in its PR:
              <a href="https://github.com/Ericsson/codechecker/pull/3849" target="_blank">#3849</a>.
            `
          }
        ]
      },
      {
        title:
          "Removed deprecated flags, turn missing checker warnings to errors",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              Removed <code>CodeChecker checkers --only-enabled</code>, use
              <code>CodeChecker checkers --details</code> instead.
              <br>
              Removed <code>CodeChecker checkers --only-disabled</code>, use
              <code>CodeChecker checkers --details</code> instead.
              <br>
              Removed <code>CodeChecker cmd diff --suppressed</code> and
              <code>CodeChecker cmd diff -s</code>, use
              <code>CodeChecker cmd diff --review-status [REVIEW_STATUS [REVIEW_STATUS ...]]</code>
              instead.
              <br>
              Removed <code>CodeChecker cmd diff --filter</code>, use
              <code>CodeChecker cmd diff --review-status false_positive</code>
              instead.
              <br>
              Removed <code>CodeChecker cmd sum --disable-unique</code>, use
              <code>CodeChecker cmd sum --uniqueing</code> instead.
              <br>
              Removed <code>CodeChecker analyze --tidy-config</code>, use
              <code>CodeChecker analyze --analyzer-config</code> instead.
              <br>
              Incorrect checker names now emit errors instead of warnings, but
              if necessary, the old behaviour can be restored with
              <code>--no-missing-checker-error</code>.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.21.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.21.0",
    features: [
      {
        title: "Support Roslynator in the report-converter",
        blocks: [
          {
            type: "text",
            value: `
              The
              <a href="https://github.com/JosefPihrt/Roslynator" target="_blank">Roslynator</a>
              project contains several analyzers for C# built on top of
              Microsoft Roslyn. CodeChecker now supports the visualization of
              these C# analysis results. It also provides a
              <a href="https://github.com/JosefPihrt/Roslynator#roslynator-command-line-tool-" target="_blank">.NET tool</a>
              for running Roslyn code analysis from the command line. It is not
              limited to Microsoft and Roslynator analyzers, it supports any
              Roslyn analyzer. It can also report MSBuild compiler diagnostics.
            `
          }
        ]
      },
      {
        title: "Optimizations to CodeChecker store and CodeChecker cmd diff",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                After a round of optimizations on
                <code>CodeChecker store</code>, we expect it to be 2x faster in
                certain cases (especially for larger projects)!
              </p>
              <p>
                For runs with a lot of reports,
                <code>CodeChecker cmd diff</code> should be faster as well.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.20.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.20.0",
    features: [
      {
        title: "Cppcheck support in CodeChecker",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                <code>CodeChecker analyze</code> sub-command was originally
                designed to drive ClangSA and ClangTidy analyzers. Now it has
                been extended with Cppcheck support.
              </p>
              <p>
                The output of the <code>CodeChecker version -o json</code>
                command wasn't a valid JSON format. From this release
                CodeChecker will provide a valid JSON output for this command.
              </p>
            `
          }
        ]
      },
      {
        title: "Change review status handling",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Review status is a categorization of reports by the developers.
                They can indicate whether a report is false-positive, confirmed,
                intentional, etc. These markings were bound to a report hash, so
                different reports sharing the same hash were attached the same
                review status. The problem with this approach was that review
                status comments written in the source code could have swapped
                review statuses back and forth if different review status was
                attached to the same bug in different runs.
              </p>
              <p>
                In this release a review status is attached to each report
                individually, so a review status given in source code comment
                doesn't affect reports with the same hash in other runs.
              </p>
              <p>
                Review status can still be set via GUI. This works like an
                e-mail rule: when a new report appears with the given hash, the
                review status will be applied automatically.
              </p>
            `
          }
        ]
      },
      {
        title: "Filter by files anywhere on bugpath",
        blocks: [
          {
            type: "text",
            value: `
              At file and source component filters reports can be selected where
              the bug path ends in those files or source components. In this
              release these file filters can be applied to any point of the bug
              path.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.19.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.19.0",
    features: [
      {
        title: "Fix JSON format of CodeChecker version subcommand",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <p>
                The output of the <code>CodeChecker version -o json</code>
                command wasn't a valid JSON format. From this release
                CodeChecker will provide a valid JSON output for this command.
              </p>
              <p>
                For more information see the
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/web/user_guide.md#json-format" target="_blank">documentation</a>.
              </p>
            `
          }
        ]
      },
      {
        title: "Not allowing disabling modeling checkers in ClangSA",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <p>
                When a Clang Static Analyzer checker is disabled in CodeChecker,
                clang is invoked with the
                <code>analyzer-disable-checker</code> flag. This allows the user
                disabling core modeling checkers such as
                <i>unix.DynamicMemoryModeling</i>. This causes malfunctioning of
                depending checkers.
              </p>
              <p>
                From this release modeling and debug checkers (listed with
                <code>clang -cc1 -analyzer-checker-help-developer</code>) will
                not be listed and cannot be disabled through CodeChecker with
                the <code>--enable</code> and <code>--disable</code> flags.
              </p>
              <p>
                They can be enabled/disabled through the Clang Static Analyzer
                specific <code>--saargs</code> flag only.
              </p>
            `
          }
        ]
      },
      {
        title: "Add --print-steps option to CodeChecker cmd diff command",
        blocks: [
          {
            type: "text",
            value: `
              Without bug steps it is hard to understand the problem by a
              programmer. With this commit we will introduce a new option for
              the <code>CodeChecker cmd diff</code> command which can be used to
              print bug steps similar to what we are doing at the
              <code>CodeChecker parse</code> command. This patch also solves the
              problem to print bug steps in <i>HTML</i> files for reports which
              come from a <i>CodeChecker server</i>.
            `
          }
        ]
      },
      {
        title: "Support YAML CodeChecker configuration files",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Multiple subcommands have a <b>--config</b> option which allows
                the configuration from an explicit configuration file. The
                parameters in the config file will be emplaced as command line
                arguments. Previously we supported only JSON format but the
                limitation of this format is that we can't add comments in this
                file for example why we enabled/disabled a checker, why an
                option is important etc.
              </p>
              <p>From this release we will also support <b>YAML</b> format:</p>
            `
          },
          {
            type: "code",
            value: `analyzer:
  # Enable/disable checkers.
  - --enable=core.DivideZero`
          },
          {
            type: "text",
            value: `
              <p>
                For more information see the
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/config_file.md#yaml" target="_blank">documentation</a>.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.18.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.18.0",
    features: [
      {
        title: "Changed JSON output format of parse and cmd diff",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              The <i>JSON</i> output of the CodeChecker parse command was not
              stable enough and the structure was very similar to the plist
              structure. Our plan is to support reading/parsing/storing of
              multiple analyzer output types not only plist but for example
              <a href="http://docs.oasis-open.org/sarif/sarif/v2.0/csprd01/sarif-v2.0-csprd01.html" target="_blank">sarif</a>
              format as well. For this reason we changed the format of the JSON
              output of the <i>CodeChecker parse</i> and
              <i>CodeChecker cmd diff</i> commands. For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/user_guide.md" target="_blank">see</a>.
            `
          }
        ]
      },
      {
        title: "Get access controls",
        blocks: [
          {
            type: "text",
            value: `
              Create a new global role (<code>PERMISSION_VIEW</code>) which will
              be used to allow the users to fetch access control information
              from a running <i>CodeChecker server</i> by using the
              <code>CodeChecker cmd permissions</code> subcommand.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.17.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.17.0",
    features: [
      {
        title: "Git blame integration",
        blocks: [
          {
            type: "text",
            value: `
              With this feature it will be possible for a developer to check who
              modified the source line last where a CodeChecker error appears.
              <ul>
                <li>
                  If the project which was analyzed is a git repository
                  <code>CodeChecker store</code> command will store blame
                  information for every source file which is not stored yet.
                </li>
                <li>
                  The GUI will have a button on the report detail view to show
                  blame information alongside the source file.
                </li>
                <li>
                  Hovering the mouse over a blame line, commit details will be
                  shown in a pop-up window. Clicking on the hash will jump to the
                  remote url of the repository and shows the commit which is
                  related to a blame line.
                </li>
              </ul>
            `
          },
          { type: "image", value: "git_blame.png" }
        ]
      },
      {
        title: "Cleanup plans",
        blocks: [
          {
            type: "text",
            value: `
              Cleanup plans can be used to track progress of reports in your
              product. The conception is similar to the
              <i>Github Milestones</i>. You can do the following:
              <ul>
                <li>
                  <strong>Managing cleanup plans</strong>: you can create
                  cleanup plans by clicking on the pencil icon at the
                  <i>Cleanup plan</i> filter on the <i>Reports page</i>. A pop-up
                  window will be opened where you can add, edit, close or remove
                  existing cleanup plans.
                </li>
                <li>
                  <strong>Add reports to a cleanup plan</strong>: you can add
                  multiple reports to a cleanup plan on the <i>Reports page</i>
                  or on the <i>Report detail page</i> by clicking to the
                  <i>Set cleanup plan</i> button and selecting a cleanup plan.
                  <i>Note</i>: you can remove reports from a cleanup plan the
                  same way by clicking on the cleanup plan name.
                </li>
                <li>
                  <strong>Filter reports by cleanup plans</strong>: you can
                  filter reports by a cleanup plan by using the
                  <i>Cleanup plan filter</i> on the <i>Reports page</i>. Using
                  this filter with other filters (<i>Detection status</i>,
                  <i>Review status</i> etc.) you will be able to filter active /
                  resolved reports in your cleanup plan.
                </li>
              </ul>
            `
          },
          { type: "image", value: "list_of_cleanup_plans.png" },
          { type: "image", value: "assign_reports_to_cleanup_plan.png" }
        ]
      },
      {
        title: "Local diff workflow support",
        blocks: [
          {
            type: "text",
            value: `
              If you want to use CodeChecker in your project but you don't want
              to run a CodeChecker server and to fix every report found by
              CodeChecker for the first time (legacy findings) with this feature
              you can do the following:
              <ul>
                <li>
                  Analyze your project to a report directory as usual (e.g.:
                  <i>./reports</i>).
                </li>
                <li>
                  Create a <i>baseline file</i> from the reports which contains
                  the legacy findings:
                  <code>CodeChecker parse ./reports -e baseline -o reports.baseline</code>.
                  <i>Note</i>: it is recommended to store this baseline file
                  (<i>reports.baseline</i>) in your repository.
                </li>
                <li>
                  On source code changes after your project is re-analyzed use
                  the <code>CodeChecker diff</code> command to get the new
                  reports:
                  <code>CodeChecker cmd diff -b ./reports.baseline -n ./reports --new</code>
                </li>
                <li>
                  On configuration changes (new checkers / options are enabled /
                  disabled, new CodeChecker / clang version is used, etc.)
                  re-generate the baseline file (step 1-2).
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "LeakSanitizer Parser",
        blocks: [
          {
            type: "text",
            value: `
              The <i>report-converter</i> tool is extended with LeakSanitizer
              which is a run-time memory leak detector for C programs.
            `
          },
          {
            type: "code",
            value: `# Compile your program.
clang -fsanitize=address -g lsan.c

# Run your program and redirect the output to a file.
ASAN_OPTIONS=detect_leaks=1 ./a.out > lsan.output 2>&1

# Generate plist files from the output.
report-converter -t lsan -o ./lsan_results lsan.output

# Store reports.
CodeChecker store ./lsan_results -n lsan`
          }
        ]
      },
      {
        title: "Checker label",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Previously the properties of checkers (<i>severity</i>,
                <i>profile</i>, <i>guideline</i>) are read from several JSON
                files. The goal was to handle all these and future properties of
                checkers in a common manner. This new solution uses labels which
                can be added to checkers.
              </p>
              <p>
                The collection of labels is found in <i>config/labels</i>
                directory. The goal of these labels is that you can enable or
                disable checkers by these labels.
              </p>
            `
          },
          {
            type: "code",
            value: `# List checkers in "sensitive" profile.
CodeChecker checkers --label profile:sensitive

# List checkers in "HIGH" severity.
CodeChecker checkers --label severity:HIGH

# List checkers covering str34-c SEI-CERT rule.
CodeChecker checkers --label sei-cert:str-34-c

# List checkers covering all SEI-CERT rules.
CodeChecker checkers --label guideline:sei-cert

# List available profiles, guidelines and severities.
CodeChecker checkers --profile
CodeChecker checkers --guideline
CodeChecker checkers --severity

# List labels and their available values.
CodeChecker checkers --label
CodeChecker checkers --label severity

# Enable HIGH checkers during analysis.
CodeChecker analyze \\
  ./compile_commands.json \\
  -o ./reports
  -e severity:HIGH`
          },
          {
            type: "text",
            value: `
              Note: with this new feature we also added severity levels for
              <i>pylint</i> and <i>cppcheck</i> analyzers.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.16.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.16.0",
    features: [
      {
        title: "PyPI package support",
        blocks: [
          {
            type: "text",
            value: `
              <i>PyPI</i> is the most commonly used central repository for Python
              packages. For this reason from this release we will provide an
              official
              <a href="https://pypi.org/project/codechecker/" target="_blank">PyPI package</a>
              for CodeChecker. This PyPI package can be easily installed on both
              <i>Unix</i> and <i>Windows</i> based systems easily by using the
              pip command: <code>pip install codechecker</code>.
            `
          }
        ]
      },
      {
        title: "Add compilation database generator for Bazel",
        blocks: [
          {
            type: "text",
            value: `
              CodeChecker was extended with a tool that can capture compilation
              database of a <b>Bazel</b> built product without actually
              performing compilation. For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/tools/bazel.md" target="_blank">see</a>.
            `
          }
        ]
      },
      {
        title: "Exporter/importer command for CodeChecker cmd",
        blocks: [
          {
            type: "text",
            value: `
              New command line options are introduced
              (<code>CodeChecker cmd export</code> and
              <code>CodeChecker cmd import</code>) which can be used to export
              comments and review status for a particular run in a JSON based
              format from a running CodeChecker server and import it to another
              server.
            `
          },
          {
            type: "code",
            value: `# Export data from one server.
CodeChecker cmd export \\
  -n myrun \\
  --url https://first-server.codechecker.com:443 \\
  2>/dev/null | python -m json.tool > myrun_export.json

# Import data to another server.
CodeChecker cmd import \\
  -i myrun_export.json \\
  --url https://second-server.codechecker.com:443`
          }
        ]
      },
      {
        title: "Sparse and Cpplint analyzers support",
        blocks: [
          {
            type: "text",
            value: `
              The <i>report-converter</i> tool was extended with two more
              analyzers:
              <ul>
                <li>
                  Sparse which is a semantic checker for C programs; it can be
                  used to find a number of potential problems with kernel code.
                </li>
                <li>
                  CppLint which is a lint-like tool which checks C++ code against
                  Google C++ Style Guide.
                </li>
              </ul>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.15.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.15.0",
    features: [
      {
        title: "Web UI",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  There is a brand new
                  <strong>Product Statistics Overview</strong> page with the
                  information about the recently introduced or resolved reports
                  or about the distribution of the reports in the product.
                </li>
                <li>
                  The <strong>Run History</strong> list was moved from a
                  separate tab to an <strong>expandable list</strong> under each
                  run at the run list. This makes it easier to find the relevant
                  run history entries for each run.
                </li>
                <li>
                  New <strong>Report Info Button</strong> to show more
                  information about a report at the report details page (run
                  name, detection/fix date ...).
                </li>
                <li>
                  Source components can be used to create and save file path
                  filters with a name to show results only from those parts of
                  the analyzed project. With the newly introduced
                  <strong>Other component</strong> every report which does not
                  belong to any other component can be filtered.
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Command line interface (CLI)",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  <strong>New exit status</strong> numbers for the CodeChecker
                  analyze and check commands for better <i>CI integration</i>:
                  <ul>
                    <li>0 - Successful analysis and no new reports</li>
                    <li>1 - CodeChecker error</li>
                    <li>
                      2 - At least one report emitted by an analyzer and there
                      is no analyzer failure
                    </li>
                    <li>3 - Analysis of at least one translation unit failed</li>
                  </ul>
                </li>
                <li>
                  <strong>Gerrit output</strong> format is available
                  <strong>for the parse subcommand</strong>. This output format
                  was only available for the CodeChecker cmd diff command in the
                  previous releases. With this change the parse command can be
                  used for the gerrit integration too.<br>
                  <code>CodeChecker parse analyzer_reports -e gerrit</code>
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Report storage support for new source code analyzers",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  Report conversion and storage support is available for
                  multiple new source code analyzer tools
                  (<strong>Coccinelle</strong>, <strong>Smatch</strong>,
                  <strong>Kernel-Doc</strong>). The
                  <a href="https://github.com/Ericsson/codechecker/tree/master/tools/report-converter" target="_blank">report-converter</a>
                  tool can be used to convert the output of these analyzers to a
                  format which can be stored to the web server or processed by
                  other CodeChecker commands (parse, cmd diff ...).
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Changes",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  Open reports date filter was renamed to
                  <i>"Outstanding reports on a given date"</i> on the web UI.<br>
                  Also a new <code>--outstanding-reports-date</code> CLI filter
                  argument was introduced as a filter option.
                </li>
                <li>
                  Less code styling related checker groups are enabled by
                  <code>--enable-all</code> flag. The
                  <code>--enable-all</code> flag enabled a lot of style checkers
                  which could generate a lot of styling reports.
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Further improvements worth mentioning",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>Allow users to overwrite location of the session file.</li>
                <li>
                  Show how many filter items are visible at the filter tool tip
                  if there are more items.
                </li>
                <li>Show selected filter items at Review status filter.</li>
                <li>Improve component statistics page load performance.</li>
                <li>
                  Enable search and highlight occurrences of the selected text
                  at the source code view.
                </li>
                <li>
                  Set analyzer name for clang-diagnostic checkers when the
                  reports are stored.
                </li>
                <li>
                  Reintroduce skipfile script for gerrit integration to be able
                  to analyze only the changed files.
                </li>
                <li>
                  New severity levels for
                  cppcoreguidelines-prefer-member-initializer,
                  altera-struct-pack-align and
                  bugprone-redundant-branch-condition checkers.
                </li>
              </ul>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.14.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.14.0",
    features: [
      {
        title: "New statistics page in the Web UI",
        blocks: [
          {
            type: "text",
            value: `
              The statistics page got a new design with a lot of new features:
              <ul>
                <li>
                  Statistics shown in separate tabs instead of one page for
                  better visibility.
                </li>
                <li>
                  New, component statistics page, where reports are distributed
                  per statistics, components can represent a part of a repository
                  (directory, files).
                </li>
                <li>
                  Statistics comparison mode: you will be able to compare the
                  report statistics of two different analysis runs or time
                  snapshots.
                </li>
                <li>
                  Diff and review status filters are available on the statistics
                  page.
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Redesigned date selectors for the web UI filter and CLI",
        blocks: [
          {
            type: "text",
            value: `
              You will be able to list the open reports of your project for any
              date. Open reports at a date are which were <i>DETECTED BEFORE</i>
              the given date and <i>NOT FIXED BEFORE</i> the given date.<br>
              From the CLI the open reports can be queried like this:<br>
              <code>CodeChecker cmd results --open-reports-date 2020:09:11:12:20 --url ...</code>
            `
          }
        ]
      },
      {
        title: "Remember filters when navigate between pages",
        blocks: [
          {
            type: "text",
            value: `
              Filters are remembered during navigating between the pages. The
              report list and statistics related filters are saved separately.
            `
          }
        ]
      },
      {
        title: "Show analyzer name alongside the reports",
        blocks: [
          {
            type: "text",
            value: `
              Analysis results from multiple static analyzers can be stored to
              the database, with this change for each report the analyzer name
              can be viewed which produced the result.
            `
          }
        ]
      },
      {
        title: "Always show similar reports",
        blocks: [
          {
            type: "text",
            value: `
              Reports with the same hash can be seen in a drop down list for each
              report without uniqueing.
            `
          }
        ]
      },
      {
        title:
          "Enable and disable checker profiles and guidelines in the analyzer CLI",
        blocks: [
          {
            type: "text",
            value: `
              There is a new syntax extended with guideline support which can be
              used to enable checker sets. With the new syntax the checkers,
              profiles and guideline can be enabled or disabled even if there is
              a conflict in their name. Their arguments may start with
              <i>checker:</i>, <i>prefix:</i>, <i>profile:</i>,
              <i>guideline:</i> or any existing label type as a namespace which
              makes the choice explicit. Without namespace it can be a checker
              name, a checker prefix, a profile name or a guideline name. In case
              of ambiguity, namespace is expected.
            `
          },
          {
            type: "code",
            value:
              "CodeChecker analyze -o reports -e profile:sensitive -e guideline:sei-cert compile_command.json"
          },
          {
            type: "text",
            value: `
              Use these commands to list the available profiles:<br>
              <code>CodeChecker checkers --profile list</code><br>
              or guidelines:<br>
              <code>CodeChecker checkers --guideline</code>
            `
          }
        ]
      },
      {
        title: "New report converter for Markdownlint results",
        blocks: [
          {
            type: "text",
            value: `
              The reports from Markdownlint can be converted and stored to the
              report server like this:
            `
          },
          {
            type: "code",
            value: `# Run Markdownlint.
mdl /path/to/your/project > ./mdl_reports.out

# Use 'report-converter' to create a CodeChecker report directory from the
# analyzer result of Markdownlint.
report-converter -t mdl -o ./codechecker_mdl_reports ./mdl_reports.out

# Store Markdownlint reports with CodeChecker.
CodeChecker store ./codechecker_mdl_reports -n mdl`
          }
        ]
      },
      {
        title: "New parse section in the CodeChecker config file",
        blocks: [
          {
            type: "text",
            value: `
              The codechecker config file was extended with a parse section
              which can be used by the parse subcommand. It can be used to set
              the path prefixes in the CodeChecker config file which should be
              trimmed by the parse subcommand when the reports are printed:
            `
          },
          {
            type: "code",
            value: `{
  "parse": [
    "--trim-path-prefix",
    "/$HOME/workspace"
  ]
}`
          },
          {
            type: "text",
            value: `
              The config file for the parse command can be set like this:
              <code>CodeChecker parse report --config codechecker_cfg.json</code>
            `
          }
        ]
      },
      {
        title: "Environment variables can be used in the CodeChecker config file",
        blocks: [
          {
            type: "text",
            value: `
              Environment variables can be used in the CodeChecker config file,
              they will be expanded automatically:
            `
          },
          {
            type: "code",
            value: `{
  "analyzer": [
    "--skip=$HOME/project/skip.txt"
  ]
}`
          }
        ]
      },
      {
        title:
          "On-demand Cross Translation Unit Analysis will be the default CTU analysis mode",
        blocks: [
          {
            type: "text",
            value: `
              The On-demand CTU analysis support introduced in the previous
              release is enabled by default now if the used Clang Static Analyzer
              supports it. CTU analysis will be performed without the huge
              temporary disc space allocation.<br>
              With the <i>--ctu-ast-mode</i> the analysis mode can be switched
              back to the old behavior if the new consumes too much memory:<br>
              <code>CodeChecker analyze --ctu-ast-mode lod-from-pch ....</code>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.13.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.13.0",
    features: [
      {
        title: "New web UI",
        blocks: [
          {
            type: "text",
            value: `
              In this release the UI framework was completely replaced to
              increase usability, stability and performance.<br>
              The new framework allows a lot of improvements like:
              <ul>
                <li>faster page load</li>
                <li>faster navigation</li>
                <li>improved front-end testing</li>
                <li>less load on the server</li>
              </ul>
              With the new UI the permalinks are backward compatible so the
              saved URLs should work as before.<br>
              Additionally to the UI improvements there is a new feature.<br>
              If <i>Unique reports</i> is enabled on the reports view there is a
              drop down list for each report showing the similar reports with
              the same report hash (but maybe with a different execution
              path).<br>
              <b>Note!</b> When building the package nodejs newer than v10.14.2
              is required! Please check the install guide for further
              instructions on how to install the dependencies.
            `
          }
        ]
      },
      {
        title: "Apply checker fixits",
        blocks: [
          {
            type: "text",
            value: `
              Some checkers in
              <a href="https://clang.llvm.org/extra/clang-tidy/" target="_blank">Clang-Tidy</a>
              can provide source code changes (fixits) to automatically modify
              the source code and fix a report. This feature can also be used to
              modernize the source code. To use this feature the
              <i>clang-tidy</i> analyzer and the
              <i>clang-apply-replacements</i> tools need to be available in the
              PATH.<br>
              During the clang-tidy analyzer execution the fixits are
              automatically collected.
            `
          },
          {
            type: "code",
            value:
              "CodeChecker analyze -o report_dir -j4 -e modernize -e performance -e readability compile_command.json --analyzers clang-tidy"
          },
          {
            type: "text",
            value: `
              Use the <code>CodeChecker fixit report_dir</code> command to list
              all collected fixits.<br>
              Fixits can be applied for a source file automatically like this:
              <code>CodeChecker fixit report_dir --apply --file "*mylib.h"</code>
              or in interactive mode where every source code modification needs
              to be approved:
              <code>CodeChecker fixit report_dir --interactive --file "*mylib.h"</code><br>
              Fixits can be applied based on a checker name, so to cleanup all
              the <i>readability-redundant-declaration</i> results execute this
              command:
              <code>CodeChecker fixit report_dir --apply --checker-name readability-redundant-declaration</code>
            `
          }
        ]
      },
      {
        title: "Coding guideline mapping to checkers (SEI-CERT)",
        blocks: [
          {
            type: "text",
            value: `
              There are coding guidelines like
              <a href="https://cmu-sei.github.io/secure-coding-standards/" target="_blank">SEI-CERT</a>,
              <a href="https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines" target="_blank">C++ Core Guidelines</a>,
              etc.) which contain best practices on avoiding common programming
              mistakes. To easily identify which checker maps to which guideline
              the <i>--guideline</i> flag was introduced.<br><br>
              To list the available guidelines where the mapping was done, use
              this command:
              <code>CodeChecker checkers --guideline</code><br><br>
              The checkers which cover a selected guideline can be listed like
              this:
              <code>CodeChecker checkers --guideline sei-cert</code><br><br>
              If we want to get which checker checks the sei-cert rule
              <i>err55-cpp</i> by executing the command below we can get that the
              <i>bugprone-exception-escape</i> checker should be enabled if the
              <i>err55-cpp</i> rule needs to be checked.
              <code>CodeChecker checkers --guideline err55-cpp bugprone-exception-escape</code><br><br>
              More detailed information about the checkers and the guideline
              mapping can be found by executing this command:<br>
              <code>CodeChecker checkers --guideline sei-cert --details</code>
            `
          }
        ]
      },
      {
        title: "Makefile output",
        blocks: [
          {
            type: "text",
            value: `
              CodeChecker can generate a Makefile without executing the
              analysis. The Makefile will contain all the necessary analysis
              commands as build targets. With this Makefile the analysis can be
              executed by <b>make</b> or by some distributed build system which
              can use a Makefile to distribute the analysis commands.<br>
              Locally with a simple <code>make</code> it can be executed like
              this:
            `
          },
          {
            type: "code",
            value: `CodeChecker analyze --makefile -o makefile_reports compile_command.json
make -f makefile_reports/Makefile -j8`
          }
        ]
      },
      {
        title: "On demand CTU analysis support",
        blocks: [
          {
            type: "text",
            value: `
              With this new flag (<b>--ctu-ast-mode</b>) the user can choose the
              way ASTs are loaded during CTU analysis.<br>
              There are two options:
              <ul>
                <li>
                  <b>load-from-pch</b> (the default behavior now, works with
                  older clang versions v9 or v10)
                </li>
                <li>
                  <b>parse-on-demand</b> (needs clang master branch or clang 11)
                </li>
              </ul>
              The mode <b>load-from-pch</b> can use significant disk-space for
              the serialized ASTs. By using the <b>parse-on-demand</b> mode some
              runtime CPU overhead can incur in the second phase of the analysis
              but much less disk space is used.<br>
              Execute this command to enable the <b>on-demand</b> mode:
              <code>CodeChecker analyze -j4 -o reports_ctu_demand --ctu --ctu-ast-mode parse-on-demand</code><br>
              See the
              <a href="https://github.com/Ericsson/codechecker/pull/2240" target="_blank">pull request</a>
              for more information.
            `
          }
        ]
      },
      {
        title: "Disable all warnings like checker groups",
        blocks: [
          {
            type: "text",
            value: `
              Clang compiler warnings are reported (Clang Tidy) by checker names
              starting with <b>clang-diagnostic-</b>. Disabling them could be
              done previously only one-by-one. In this release the warnings can
              be disabled now with the corresponding checker group.
              <code>CodeChecker analyze --analyzers clang-tidy -d clang-diagnostic</code>
            `
          }
        ]
      },
      {
        title: "IPv6 support",
        blocks: [
          {
            type: "text",
            value: `
              The CodeChecker server can be configured to listen on IPv6
              addresses.
            `
          }
        ]
      },
      {
        title: "Performance improvements",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  diff command printing out source code lines got a performance
                  improvement
                </li>
                <li>report storage performance got improved</li>
              </ul>
            `
          }
        ]
      },
      {
        title: "--ctu-reanalyze-on-failure flag deprecated",
        breaking: true,
        blocks: [
          {
            type: "text",
            value: `
              <b>--ctu-reanalyze-on-failure</b> flag is marked as deprecated and
              it will be removed in one of the upcoming releases.<br>
              It will be removed because the
              <a href="https://clang.llvm.org/docs/analyzer/user-docs/CrossTranslationUnit.html" target="_blank">Cross Translation Unit (CTU)</a>
              analysis functionality got more stable in the Clang Static
              analyzer so this feature can be removed.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.12.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.12.0",
    features: [
      {
        title: "Show Clang Tidy reports in headers",
        blocks: [
          {
            type: "text",
            value: `
              Clang Tidy reports are shown from headers (non system) now, this
              change can increase the number of new results! Use the following
              analyzer configuration to turn back the old behavior by setting
              the <i>HeaderFilterRegex</i> value to an empty string:
              <code>CodeChecker analyze compile_command.json --analyzer-config clang-tidy:HeaderFilterRegex=""</code>
            `
          }
        ]
      },
      {
        title: "Python 3 only",
        blocks: [
          {
            type: "text",
            value: `
              Because of Python 2 sunset at the beginning of 2020 CodeChecker
              was ported to Python 3 - the minimal required version is
              <b>3.6</b>. Because of the Python version change and a lot of 3pp
              dependencies were updated it is required to remove the old and
              create a new virtual environment to build the package!
            `
          }
        ]
      },
      {
        title:
          "Store results from multiple static and dynamic analyzer tools",
        blocks: [
          {
            type: "text",
            value: `
              Starting with this version CodeChecker can store the results of
              multiple static and dynamic analyzers for different programming
              languages:
              <ul>
                <li>Facebook Infer (C/C++, Java)</li>
                <li>Clang Sanitizers (C/C++)</li>
                <li>Spotbugs (Java)</li>
                <li>Pylint (Python)</li>
                <li>Eslint (Javascript)</li>
                <li>...</li>
              </ul>
              The complete list of the supported analyzers can be found
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/supported_code_analyzers.md" target="_blank">here</a>.
              To be able to store the reports of an analyzer a
              <a href="https://github.com/Ericsson/codechecker/tree/master/tools/report-converter" target="_blank">report converter tool</a>
              is available which can convert the reports of the supported
              analyzers to a format which can be stored by the CodeChecker store
              command.
            `
          }
        ]
      },
      {
        title: "GitLab integration",
        blocks: [
          {
            type: "text",
            value: `
              Inside a GitLab Runner CodeChecker can be executed to provide a
              code quality report for each GitLab review request. The codeclimate
              json output format was added to the
              <code>CodeChecker parse</code> and
              <code>CodeChecker cmd diff</code> commands to generate a json file
              which can be parsed by GitLab as a quality report. See the
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/gitlab_integration.md" target="_blank">GitLab integration guide</a>
              for more details how to configure the GitLab runners and
              CodeChecker.
            `
          }
        ]
      },
      {
        title: "Simplify Gerrit integration",
        blocks: [
          {
            type: "text",
            value: `
              Integration was simplified, no extra output parsing and converter
              scripts are needed. The
              <code>CodeChecker cmd diff -o gerrit ...</code> command can
              generate an output format which can be sent to gerrit as a review
              result.
            `
          }
        ]
      },
      {
        title: "Bazel build system support",
        blocks: [
          {
            type: "text",
            value: `
              Compilation commands executed by the Bazel build system can now be
              logged with the CodeChecker logger to run the static analyzers on
              the source files. Check out the Bazel build system
              <a href="https://github.com/Ericsson/codechecker/blob/e506338a7e5f1b5e2d5d405e0e75584f0a645b7d/docs/analyzer/user_guide.md#bazel" target="_blank">integration guide</a>
              for more details.
            `
          }
        ]
      },
      {
        title: "Compilation errors as reports",
        blocks: [
          {
            type: "text",
            value: `
              Compilation errors occurred during the analysis are now captured
              as reports by the <b>clang-diagnostic-error</b> checker. These
              types of reports can be disabled as a normal checker like this:
              <code>CodeChecker analyze --disable clang-diagnostic-error ...</code>
            `
          }
        ]
      },
      {
        title: "Analyzer and checker configuration from the command line",
        blocks: [
          {
            type: "text",
            value: `
              The Clang and Clang Tidy static analyzers and the checkers can be
              configured from the command line with the newly introduced
              <b>--analyzer-config</b> and <b>--checker-config</b> options.
            `
          }
        ]
      },
      {
        title: "Analyzer configuration",
        blocks: [
          {
            type: "text",
            value: `
              Use these commands to list the available analyzer config options
              (use the <b>--details</b> flag for the default values and more
              description):
              <ul>
                <li>
                  <code>CodeChecker analyzers --analyzer-config clangsa</code>
                </li>
                <li>
                  <code>CodeChecker analyzers --analyzer-config clang-tidy</code>
                </li>
              </ul>
              A Clang Static Analyzer configuration option can be enabled during
              analysis like this:
              <code>CodeChecker analyze compile_command.json -o reports --analyzer-config clangsa:suppress-c++-stdlib=false -c</code>
            `
          }
        ]
      },
      {
        title: "Checker configuration",
        blocks: [
          {
            type: "text",
            value: `
              Use the <code>CodeChecker checkers --checker-config</code> command
              to list the checker options, or the
              <code>CodeChecker checkers --checker-config --details</code>
              command to get the checker options with the default values. A
              checker option can be set like this:
              <code>CodeChecker analyze compile_command.json -o reports -e cplusplus.Move --checker-config clangsa:cplusplus.Move:WarnOn="All"</code>
            `
          }
        ]
      },
      {
        title:
          "Select only a few files to be analyzed from the compile command database",
        blocks: [
          {
            type: "text",
            value: `
              There is no need for a complex skip file or to create smaller
              compile command database files to execute the analysis only on a
              few files. With the <b>--file</b> option the important files can be
              selected - the analysis for the other files will be skipped:
              <code>CodeChecker analyze compile_command.json --file "*main.cpp" "*lib.cpp"</code>
            `
          }
        ]
      },
      {
        title:
          "Incremental Analysis Extension: analyze c/cpp files that are dependencies of a changed header",
        blocks: [
          {
            type: "text",
            value: `
              Header files can not be analyzed without a c/cpp file. If a skip
              file contains a header file (with a "+" tag) like this:
            `
          },
          {
            type: "code",
            value: `+*lib.h
-*`
          },
          {
            type: "text",
            value: `
              Which means the header file should be analyzed. CodeChecker tries
              to find all the c/cpp files including that header file and execute
              the analysis on those c/cpp files too so the header file will be
              analyzed. The only limitation is that the full compilation database
              is required to collect this information.
            `
          }
        ]
      },
      {
        title: "CodeChecker CLI configuration files",
        blocks: [
          {
            type: "text",
            value: `
              The CodeChecker commands can be saved in a config file which can be
              put into a version control system or distributed between multiple
              developers much easier. In the previous release v6.11.0 the support
              for the analyzer configuration file was added. In this release it
              was extended to the web server related commands (store, server) so
              they can be stored into a configuration file too. It is not
              required to type out the options in the command line all the time
              to store the analysis reports. With an example
              <code>store_cfg.json</code> config file like this:
            `
          },
          {
            type: "code",
            value: `{
  "store":
    [
      "--name=run_name",
      "--tag=my_tag",
      "--url=http://codechecker.my/MyProduct"
    ]
}`
          },
          {
            type: "text",
            value: `
              The CodeChecker store command can be this short:
              <code>CodeChecker store reports --config store_cfg.json</code>
            `
          }
        ]
      },
      {
        title: "Other new features worth mentioning",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>
                  The review comments in the source code are shown by the
                  <code>CodeChecker parse</code> command.
                </li>
                <li>
                  A free text description can be stored to every run which can
                  contain any compilation or analysis related description.
                  <code>CodeChecker store --description "analysis related extra information" ...</code>
                </li>
              </ul>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.11.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.11.0",
    features: [
      {
        title: "Show system comments for bugs",
        blocks: [
          {
            type: "text",
            value: `
              Review status changes by the users are automatically stored and
              shown at the report comment section for each report. With this
              feature the status changes of the reports can be easily tracked.
            `
          }
        ]
      },
      {
        title:
          "Introduce different compiler argument filtering if the original compiler was clang",
        blocks: [
          {
            type: "text",
            value: `
              If the original compiler used to build a project was clang/clang++
              only a minimal compilation flag filtering or modification is done.
              In the case where the original compiler was gcc/g++ many non
              compatible compiler flags were filtered which is not required if
              the original compiler is clang.
            `
          }
        ]
      },
      {
        title: "Store the Cppcheck plist reports",
        blocks: [
          {
            type: "text",
            value: `
              Plist reports generated by Cppcheck can be stored by the
              <code>CodeChecker store</code> command. For a more detailed example
              how to configure Cppcheck to generate the reports in the right
              format see the
              <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/docs/cppcheck.md" target="_blank">documentation</a>.
            `
          }
        ]
      },
      {
        title: "CodeChecker config file support for the analysis arguments",
        blocks: [
          {
            type: "text",
            value: `
              The arguments for a <code>CodeChecker analyze</code> command can be
              given in a config file. A more detailed description about the usage
              and the config file format can be found
              <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/docs/analyzer/user_guide.md#analyzer-configuration-file" target="_blank">here</a>.
            `
          }
        ]
      },
      {
        title: "Log compile commands with absolute paths",
        blocks: [
          {
            type: "text",
            value: `
              With the introduction of a new environment variable
              (<b>CC_LOGGER_ABS_PATH</b>) the compiler include paths will be
              converted to an absolute path. This conversion can be necessary if
              the compiler command database created by CodeChecker will be used
              by other static analyzers (E.g. <i>Cppcheck</i>). For more
              information
              <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/analyzer/tools/build-logger#cc_logger_abs_path" target="_blank">see</a>.
            `
          }
        ]
      },
      {
        title: "Enforce taking the analyzers from PATH",
        blocks: [
          {
            type: "text",
            value: `
              With the newly introduced environment variable
              (<b>CC_ANALYZERS_FROM_PATH</b>) the usage of the static analyzers
              in the PATH can be forced even if the configuration contains
              analyzers not from the PATH.
            `
          }
        ]
      },
      {
        title: "List ClangSA checker options",
        blocks: [
          {
            type: "text",
            value: `
              The Clang Static Analyzer options can be listed now (requires clang
              v9.0.0 or newer). Use the command
              <code>CodeChecker analyzers --dump-config clangsa</code> to print
              the static analyzer configuration.
            `
          }
        ]
      },
      {
        title: "Support json output for parse command",
        blocks: [
          {
            type: "text",
            value: `
              The parse command can generate json output from the reports if
              required: <code>CodeChecker parse -e json analyzer_reports</code>.
            `
          }
        ]
      },
      {
        title: "Use CodeChecker parse with multiple directories",
        blocks: [
          {
            type: "text",
            value: `
              The <code>CodeChecker cmd parse</code> command now accepts multiple
              directories to parse the reports from.
            `
          }
        ]
      },
      {
        title: "Update the name of a run from the command line (CLI)",
        blocks: [
          {
            type: "text",
            value: `
              Allow the user to rename a run from command line. For more
              information
              <a href="https://github.com/Ericsson/codechecker/blob/dbd3feaffd389703a4c59c8d24b5f14f6d54374d/docs/web/user_guide.md#cmd-update" target="_blank">see</a>.
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.10.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.10.0",
    features: [
      {
        title: "Filter results by bug path length",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We are showing bug path length for each report at the Bug
                overview page and now it is possible to filter run results by
                bug path length on the GUI and at the command line too.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker cmd results my_run --bug-path-length 1:4</code>
                </li>
                <li>
                  <code>CodeChecker cmd results my_run --bug-path-length :10</code>
                </li>
              </ul>
            `
          },
          { type: "image", value: "bug_path_length_filter.png" }
        ]
      }
    ]
  },
  {
    version: "6.9.1",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.9.1",
    features: [
      {
        title: "Show macro definitions and notes",
        blocks: [
          {
            type: "text",
            value: `
              If a bug path goes through a macro, it is impossible to understand
              the bug path, since macro definitions cannot be resolved. Now we
              show macro expansion and notes in the web UI if your Clang version
              supports it.
            `
          },
          { type: "image", value: "macro_expansion.png" }
        ]
      }
    ]
  },
  {
    version: "6.9.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.9.0",
    features: [
      {
        title: "New detection status types",
        blocks: [
          {
            type: "text",
            value: `
              <p>We added 2 new detection types:</p>
              <ul>
                <li>
                  <b>Off</b> - were reported by a checker that is switched off
                  during the analysis.
                </li>
                <li>
                  <b>Unavailable</b> - were reported by a checker that does not
                  exist anymore because it was removed or renamed.
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Disable review status change on the WEB UI",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We can disable review status change in the web UI for each
                product to force programmers to use inline source code comments.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.8.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.8.0",
    features: [
      {
        title: "Filter results by report hash",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We are showing report hash for each report at the Bug overview
                page and now it is possible to filter run results by report hash
                on the GUI and at the command line too.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker cmd results my_run --report-hash 7084350547fcde43061bd1390ec169a9</code>
                </li>
                <li>
                  <code>CodeChecker cmd diff -b run1 -n run2 --unresolved --severity high medium --report-hash 7084350547fcde43061bd1390ec169a9</code>
                </li>
              </ul>
            `
          },
          { type: "image", value: "report_hash_filter.png" }
        ]
      },
      {
        title: "New filters at Checker statistics",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                We can get statistics only for specified runs, files, checker
                names etc. using the filter bar beside the statistic tables.
              </p>
            `
          },
          { type: "image", value: "checker_statistics.png" }
        ]
      },
      {
        title: "Delete filtered run results",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                It is possible to remove old, unneeded filtered reports by
                clicking on the <i>Remove filtered reports</i> button at the top
                of the filter bar.
              </p>
            `
          },
          { type: "image", value: "remove_filtered_reports.png" }
        ]
      },
      {
        title: "Support managing source component on the GUI",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Source components can be managed on the GUI at the Report filter
                bar after clicking on the pencil icon at the
                <i>Source component</i> filter. A pop-up window will be opened
                where you can add, edit or remove existing source components.
              </p>
            `
          },
          { type: "image", value: "list_of_source_components.png" }
        ]
      },
      {
        title: "Analysis Statistics",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                For each run the CodeChecker version (used to run the analysis)
                and the static analyzer versions along with the success/failure
                rate of the analysis can be viewed.
              </p>
            `
          },
          { type: "image", value: "analysis_statistics.png" }
        ]
      },
      {
        title: "Fine gain control of Clang warnings",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Compiler warnings are diagnostic messages that report
                constructions that are not inherently erroneous but that are
                risky or suggest there may have been an error. You can fine-tune
                which warnings to use in the analysis by setting the enabled and
                disabled flags. These flags should start with a capital
                <b>W</b> or <b>Wno-</b> prefix followed by the warning name.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker analyze /path/to/build.log -o /path/to/output/dir --enable Wunused --disable Wno-unused-parameter</code>
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "Allow comparison of two report directories",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Now we are able to compare two report directories the same way
                as remote runs by using CodeChecker command line.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker cmd diff -b /path/to/report_dir_base -n /path/to/report_dir_new --new</code>
                </li>
              </ul>
            `
          }
        ]
      },
      {
        title: "C/C++ standard auto detection",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Detect automatically which C/C++ standard was used for
                compilation by GCC and pass the relevant option to Clang (e.g.
                -std=c++11). This way the same standard version is used during
                analysis as the one in the build system even if it wasn't set
                explicitly.
              </p>
            `
          }
        ]
      }
    ]
  },
  {
    version: "6.7.0",
    url: "https://github.com/Ericsson/codechecker/releases/tag/v6.7.0",
    features: [
      {
        title: "Component filters",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Administrators of a product can create new source components by
                using <b>CodeChecker cmd components</b> subcommand which can be
                used to filter results by multiple file paths.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  Create a new component:
                  <code>CodeChecker cmd components add -i ./my_source_component.txt --description "Description of my component" my_source_component_name</code>
                </li>
                <li>
                  List all components:
                  <code>CodeChecker cmd components list</code>
                </li>
              </ul>
              For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/web/user_guide.md#source-components-components" target="_blank">see</a>.
            `
          },
          { type: "image", value: "component_filter.png" }
        ]
      },
      {
        title: "Diff two different tagged versions of the same run",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                It is possible to compare two different tagged versions of the
                same run not only different run names.
              </p>
            `
          },
          { type: "image", value: "compare_tags.png" }
        ]
      },
      {
        title: "Generate index.html file by using PlistToHTML",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Creating an index.html file that lists the found reports which
                links to the local html pages.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker parse ./reports -e html -o ./reports_html</code>
                </li>
              </ul>
              For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/usage.md#step-3" target="_blank">see</a>.
            `
          },
          { type: "image", value: "plist_to_html_index.png" }
        ]
      },
      {
        title: "Separate filter options for cmd line",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Create separate filter options for
                <b>CodeChecker cmd results</b> and
                <b>CodeChecker cmd diff</b> command line options to be more
                consistent with the UI.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  <code>CodeChecker cmd results my_run --severity critical high medium --file "/home/username/my_project/*"</code>
                  <code>CodeChecker cmd diff -b run1 -n run2 --unresolved --severity high medium --review-status unreviewed confirmed</code>
                </li>
              </ul>
              For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/web/user_guide.md#cmd" target="_blank">see</a>.
            `
          }
        ]
      },
      {
        title: "Enable passwordless token based authentication",
        blocks: [
          {
            type: "text",
            value: `
              <p>
                Command line clients can authenticate using the
                username/password stored in the
                <b>.codechecker.passwords.json</b>. It is obviously not a good
                idea to store passwords in text files. Instead of this the user
                is able to generate a token from command line, that can be used
                to authenticate in the name of his/her name.
              </p>
              <b>Examples:</b>
              <ul>
                <li>
                  Create a new token:
                  <code>CodeChecker cmd token new --description "Description of my token"</code>
                </li>
                <li>
                  List my personal access tokens:
                  <code>CodeChecker cmd token list</code>
                </li>
              </ul>
              For more information
              <a href="https://github.com/Ericsson/codechecker/blob/master/docs/web/authentication.md#personal-access-token" target="_blank">see</a>.
            `
          }
        ]
      },
      {
        title: "Consistent report counting",
        blocks: [
          {
            type: "text",
            value: `
              <ul>
                <li>Uniqueing is disabled at bug list view by default.</li>
                <li>
                  Numbers on the Run page (Number of unresolved reports,
                  Detection status) are counted without uniqueing.
                </li>
                <li>
                  Set default filter set to the following values:
                  <ul>
                    <li>
                      Review status: <b>Unreviewed</b>, <b>Confirmed</b>
                    </li>
                    <li>
                      Detection status: <b>New</b>, <b>Reopened</b>,
                      <b>Unresolved</b>
                    </li>
                  </ul>
                </li>
              </ul>
            `
          }
        ]
      }
    ]
  }
];
