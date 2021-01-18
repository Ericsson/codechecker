<template>
  <!-- eslint-disable max-len -->
  <v-container fluid>
    <v-timeline align-top>
      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item color="green lighten-1">
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.15.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.15.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Web UI
            </template>

            <ul>
              <li>
                There is a brand new
                <strong>Product Statistics Overview</strong> page
                with the information about the recently introduced or resolved
                reports or about the distribution of the reports in the
                product.
              </li>
              <li>
                The <strong>Run History</strong> list was moved from a separate
                tab to an <strong>expandable list</strong> under each run at
                the run list. This makes easier to find the relevant run
                history entries for each run.
              </li>
              <li>
                New <strong>Report Info Button</strong> to show more
                information about a report at the report details page
                (run name, detection/fix date ...).
              </li>
              <li>
                Source components can be used to create and save file path
                filters with a name to show results only from those parts
                of the analyzed project. With the newly introduced
                <strong>Other component</strong> every report which does not
                belong to any other component can be filtered.
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Command line interface (CLI)
            </template>

            <ul>
              <li>
                <strong>New exit status</strong> numbers for the CodeChecker
                analyze and check commands for better <i>CI integration</i>:
                <ul>
                  <li>
                    0 - Successful analysis and no new reports
                  </li>
                  <li>
                    1 - CodeChecker error
                  </li>
                  <li>
                    2 - At least one report emitted by an analyzer and there
                    is no analyzer failure
                  </li>
                  <li>
                    3 - Analysis of at least one translation unit failed
                  </li>
                </ul>
              </li>
              <li>
                <strong>Gerrit output</strong> format is available
                <strong>for the parse subcommand</strong>.
                This output format was only available for the CodeChecker
                cmd diff command in the previous releases. With this change
                the parse command can be used for the gerrit integration
                too.<br>
                <code>CodeChecker parse analyzer_reports -e gerrit</code>
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Report storage support for new source code analyzers
            </template>

            <ul>
              <li>
                Report conversion and storage support is available for multiple
                new source code analyzer tools (<strong>Coccinelle</strong>,
                <strong>Smatch</strong>, <strong>Kernel-Doc</strong>). The
                <a
                  href="https://github.com/Ericsson/codechecker/tree/master/tools/report-converter"
                  target="_blank"
                >
                  report-converter
                </a> tool can be used to convert the output of these analyzers
                to a format which can be stored to the web server or processed
                by other CodeChecker commands (parse, cmd diff ...).
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Changes
            </template>

            <ul>
              <li>
                Open reports date filter was renamed to
                <i>"Outstanding reports on a given date"</i> on the web UI.<br>
                Also a new <code>--outstanding-reports-date</code> CLI filter
                argument was introduced as a filter option.
              </li>
              <li>
                Less code styling related checker groups are enabled by
                <code>--enable-all</code> flag.
                The <code>--enable-all</code> flag enabled a lot of style
                checkers which could generate a lot of styling reports.
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Further improvements worth mentioning
            </template>

            <ul>
              <li>
                Allow users to overwrite location of the session file.
              </li>
              <li>
                Show how many filter items are visible at the filter tool tip
                if there are more items.
              </li>
              <li>
                Show selected filter items at Review status filter.
              </li>
              <li>
                Improve component statistics page load performance
              </li>
              <li>
                Enable search and highlight occurrences of the selected text
                at the source code view
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
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star">
        <new-release-item>
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.14.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.14.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              New statistics page in the Web UI
            </template>
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
                Statistics comparison mode: you will be able compare the report
                statistics of two different analysis runs or time snapshot
              </li>
              <li>
                Diff and review status filters are available on the statistics
                page.
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Redesigned date selectors for the web UI filter and CLI
            </template>
            You will be able to list the open reports of your project for any
            date. Open reports at a date are which were <i>DETECTED BEFORE</i>
            the given date and <i>NOT FIXED BEFORE</i> the given date.<br>
            From the CLI the open reports can be queried like this:<br>
            <code>CodeChecker cmd results --open-reports-date 2020:09:11:12:20 --url ...</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Remember filters when navigate between pages
            </template>
            Filters are remembered during navigating between the pages. The
            report list and statistics related filters are saved separately.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Show analyzer name alongside the reports
            </template>
            Analysis results from multiple static analyzers can be stored to
            the database, with this change for each report the analyzer name
            can be viewed which produced the result.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Always show similar reports
            </template>
            Reports with the same hash can be seen in a drop down list for
            each report without uniqueing.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Enable and disable checker profiles and guidelines
              (like <i>sei-cert</i>) in the analyzer CLI.
            </template>
            There is a new syntax extended with guideline support which can be
            used to enable checker sets. With the new syntax the checkers,
            profiles and guideline can be enabled or disabled even if there is
            a conflict in their name. The arguments may start with
            <i>profile:</i> of <i>guideline:</i> prefix which makes the choice
            explicit. Without prefix it means a profile name, a guideline
            name or a checker group/name in this priority order.<br>
            <code>
              CodeChecker analyze -o reports -e profile:sensitive -e guideline:sei-cert compile_command.json
            </code><br><br>
            Use these commands to list the available profiles:<br>
            <code>CodeChecker checkers --profile list</code><br>
            or guidelines:<br>
            <code>CodeChecker checkers --guideline</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              New report converter for Markdownlint results
            </template>
            The reports from Markdownlint can be converted and stored to the
            report serve like this:

            <pre>
    # Run Markdownlint.
    mdl /path/to/your/project > ./mdl_reports.out

    # Use 'report-converter' to create a CodeChecker report directory from the
    # analyzer result of Markdownlint.
    report-converter -t mdl -o ./codechecker_mdl_reports ./mdl_reports.out

    # Store Markdownlint reports with CodeChecker.
    CodeChecker store ./codechecker_mdl_reports -n mdl
            </pre>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              The codechecker config file was extended with a parse section
              which can be used by the parse subcommand.
            </template>
            It can be used to set the path prefixes in the CodeChecker config
            file which should be trimmed by the parse subcommand when the
            reports are printed:<br>
            <pre>
    {
      "parse": [
        "--trim-path-prefix",
        "/$HOME/workspace"
      ]
    }
            </pre><br>
            The config file for the parse command can be set like this:
            <code>CodeChecker parse report --config codechecker_cfg.json</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Environment variables can be used in the CodeChecker config file
            </template>
            Environment variables can be used in the CodeChecker config file,
            they will be expanded automatically:
            <pre>
    {
      "analyzer": [
        "--skip=$HOME/project/skip.txt"
      ]
    }
            </pre>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              On-demand Cross Translation Unit Analysis will be the default
              CTU analysis mode
            </template>
            The On-demand CTU analysis support introduced in the previous
            release is enabled by default now if the used Clang Static Analyzer
            supports it. CTU analysis will be performed without the huge
            temporary disc space allocation.<br>

            With the <i>--ctu-ast-mode</i> the analysis mode can be switched
            back to the old behavior if the new consumes too much memory:<br>
            <code>CodeChecker analyze --ctu-ast-mode lod-from-pch ....</code>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item color="green lighten-1">
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.13.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.13.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              New web UI
            </template>
            In this release the UI framework was completely replaced to
            increase usability, stability and performance. <br>
            The new framework allows a lot of improvements like:
            <ul>
              <li>faster page load</li>
              <li>faster navigation</li>
              <li>improved front-end testing</li>
              <li>less load on the server</li>
            </ul>
            With the new UI the permalinks are backward compatible so the saved
            URLs should work as before.<br>

            Additionally to the UI improvements there is a new feature.<br>

            If <i>Unique reports</i> is enabled on the reports view there is a
            drop down list for each report showing the similar reports with the
            same report hash (but maybe with a different execution path)<br>

            <b>Note!</b> When building the package nodejs newer than v10.14.2
            is required! Please check the install guide for further
            instructions on how to install the dependencies.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Apply checker fixits
            </template>
            Some checkers in
            <a href="https://clang.llvm.org/extra/clang-tidy/">Clang-Tidy</a>
            can provide source code changes (fixits) to automatically modify
            the source code and fix a report. This feature can also be used to
            modernize the source code. To use this feature the
            <i>clang-tidy</i> analyzer and the <i>clang-apply-replacements</i>
            tools needs to be available in the PATH. <br>
            During the clang-tidy analyzer execution the fixits are
            automatically collected.
            <code>CodeChecker analyze -o report_dir -j4 -e modernize -e
              performance -e readability compile_command.json
              --analyzers clang-tidy
            </code><br>
            Use the <code>CodeChecker fixit report_dir</code> command to list
            all collected fixits. <br>
            Fixits can be applied for a source file automatically like this:
            <code>CodeChecker fixit report_dir --apply --file "*mylib.h"</code>
            or in interactive mode where every source code modification needs
            to be approved: <code>CodeChecker fixit report_dir --interactive
              --file "*mylib.h"</code><br>

            Fixits can be applied based on a checker name, so to cleanup all
            the <i>readability-redundant-declaration</i> results execute this
            command: <code>CodeChecker fixit report_dir --apply --checker-name
              readability-redundant-declaration</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Coding guideline mapping to checkers (SEI-CERT)
            </template>
            There are  coding guidelines like
            <a href="https://wiki.sei.cmu.edu/confluence/display/seccode/SEI+CERT+Coding+Standards">SEI-CERT</a>,
            <a href="https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines">C++ Core Guidelines</a>,
            etc.) which contain best practices on avoiding common programming
            mistakes. To easily identify which checker maps to which guideline
            the <i>--guideline</i> flag was introduced.<br>
            <br>
            To list the available guidelines where the mapping was done, use
            this command: <code>CodeChecker checkers --guideline</code><br>
            <br>
            The checkers which cover a selected guideline can be listed like
            this: <code>CodeChecker checkers --guideline sei-cert</code><br>
            <br>
            If we want to get which checker checks the sei-cert rule
            <i>err55-cpp</i> by executing the command below we can get that the
            <i>bugprone-exception-escape</i> checker should be enabled if the
            <i>err55-cpp</i> rule needs to be checked.
            <code>CodeChecker checkers --guideline err55-cpp
              bugprone-exception-escape</code><br>
            <br>
            More detailed information about the checkers and the guideline
            mapping can be found by executing this command:<br>
            <code>CodeChecker checkers --guideline sei-cert --details</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Makefile output
            </template>
            CodeChecker can generate a Makefile without executing the analysis.
            The Makefile will contain all the necessary analysis commands as
            build targets. With this Makefile the analysis can be executed by
            <b>make</b> or by some distributed build system which can use a
            Makefile to distribute the analysis commands. <br>

            Locally with a simple `make` it can be executed like this:
            <code>CodeChecker analyze --makefile -o makefile_reports
              compile_command.json make -f makefile_reports/Makefile -j8</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              On demand CTU analysis support
            </template>
            With this new flag (<b>--ctu-ast-mode</b>) the user can choose the
            way ASTs are loaded during CTU analysis. <br>
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
            but uses much less disk space is used. <br>
            Execute this command to enable the <b>on-demand</b> mode:
            <code>CodeChecker analyze -j4 -o reports_ctu_demand --ctu
              --ctu-ast-mode parse-on-demand</code><br>

            See the <a href="https://github.com/Ericsson/codechecker/pull/2240">pull request</a>
            for more information.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Disable all warnings like checker groups
            </template>
            Clang compiler warnings are reported (Clang Tidy) by checker names
            staring with <b>clang-diagnostic-</b>. Disabling them could be done
            previously only one-by-one. In this release the warnings can be
            disabled now with the corresponding checker group.
            <code>CodeChecker analyze --analyzers clang-tidy -d
              clang-diagnostic</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              IPv6 support
            </template>
            The CodeChecker server can be configured to listen on IPv6
            addresses.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Performance improvements
            </template>
            <ul>
              <li>
                diff command printing out source code lines got a performance
                improvement
              </li>
              <li>report storage performance got improved</li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              DEPRECATED flag!
            </template>
            <b>--ctu-reanalyze-on-failure</b> flag is marked as deprecated and
            it will be removed in one of the upcoming releases. <br>
            It will be removed because the
            <a href="https://clang.llvm.org/docs/analyzer/user-docs/CrossTranslationUnit.html">Cross Translation Unit (CTU)</a>
            analysis functionality got more stable in the Clang Static analyzer
            so this feature can be removed.
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star">
        <new-release-item>
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.12.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.12.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Show Clang Tidy reports in headers
            </template>
            Clang Tidy reports are shown from headers (non system) now, this
            change can increase the number of new results! Use the following
            analyzer configuration to turn back the old behavior by setting the
            <i>HeaderFilterRegex</i> value to an empty string:
            <code>
              CodeChecker analyze compile_command.json --analyzer-config clang-tidy:HeaderFilterRegex=\"\"
            </code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Python 3 only
            </template>
            Because of Python 2 sunset at the beginning of 2020 CodeChecker was
            ported to Python 3 the minimal required version is <b>3.6</b>.
            Because of the Python version change and a lot of 3pp dependencies
            were updated it is required to remove the old and create a new
            virtual environment to build the package!
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Store results from multiple static and dynamic analyzer tools
            </template>
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
            <a href="https://github.com/Ericsson/codechecker/blob/master/docs/supported_code_analyzers.md">
              here
            </a>.
            To be able to store the reports of an analyzer a
            <a href="https://github.com/Ericsson/codechecker/tree/master/tools/report-converter">
              report converter tool
            </a> is available which can convert the reports of the supported
            analyzers to a format which can be stored by the CodeChecker store
            command.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              GitLab integration
            </template>
            Inside a GitLab Runner CodeChecker can executed to provide a code
            quality report for each GitLab review request. The codeclimate json
            output format was added to the <code>Codechecker parse</code> and
            <code>CodeChecker cmd diff</code> commands to generate a json file
            which can be parsed by GitLab as a quality report. See the
            <a href="https://github.com/Ericsson/codechecker/blob/master/docs/gitlab_integration.md">
              GitLab integration guide
            </a> for more details how to configure the GitLab runners and
            CodeChecker.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Simplify Gerrit integration
            </template>
            Integration was simplified, no extra output parsing and converter
            scripts are needed.  The <code>CodeChecker cmd diff -o gerrit ...</code>
            command can generate an output format which can be sent to gerrit
            as a review result.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Bazel build system support
            </template>
            Compilation commands executed by the Bazel build system can now be
            logged with the Codechecker logger to run the static analyzers on
            the source files. Check out the Bazel build system
            <a href="https://github.com/Ericsson/codechecker/blob/e506338a7e5f1b5e2d5d405e0e75584f0a645b7d/docs/analyzer/user_guide.md#bazel">
              integration guide
            </a> for more details.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Compilation errors as reports
            </template>
            Compilation errors occurred during the analysis are now captured as
            reports by the <b>clang-diagnostic-error</b> checker.  These types
            of reports can be disabled as a normal checker like this:
            <code>CodeChecker analyze --disable clang-diagnostic-error ...</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Analyzer and checker configuration from the command line
            </template>
            The Clang and Clang Tidy static analyzers and the checkers can be
            configured from the command line with the newly introduced
            <b>--analyzer-config</b> and <b>--checker-config</b> options.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Analyzer configuration
            </template>
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
            analysis like this:<br>
            <code>CodeChecker analyze compile_command.json -o reports
              --analyzer-config clangsa:suppress-c++-stdlib=false -c</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Checker configuration
            </template>
            Use the <code>CodeChecker checkers --checker-config</code> command
            to list the checker options, or the
            <code>CodeChecker checkers --checker-config --details</code>
            command to get the checker options with the default values.
            A checker option can be set like this:<br>
            <code>CodeChecker analyze compile_command.json -o reports -e
              cplusplus.Move --checker-config
              clangsa:cplusplus.Move:WarnOn="All"</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Select only a few files to be analyzed from the compile command
              database
            </template>
            There is no need for a complex skip file or to create smaller
            compile command database files to execute the analysis only on a
            few files. With the <b>--file</b> option the important files can be
            selected the analysis for the other files will be skipped:<br>
            <code>CodeChecker analyze compile_command.json --file "*main.cpp"
              "*lib.cpp"</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Incremenetal Analysis Extension: Analyze c/cpp files that are
              dependencies of a changed header
            </template>
            Header files can not be analyzed without a c/cpp file. If a skip
            file contains a header file (with a "+" tag) like this:
            <pre>
    +*lib.h
    -*
            </pre>
            Which means the header file should be analyzed. CodeChecker tries
            to find all the c/cpp files including that header file and execute
            the analysis on those c/cpp files too so the header file will be
            analyzed. The only limitation is that the full compilation database
            is required to collect this information.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              CodeChecker CLI configuration files
            </template>
            The CodeChecker commands can be saved in a config file which can be
            put into a version control system or distributed between multiple
            developers much easier. In the previous release v6.11.0 the support
            for the analyzer configuration file was added. In this release it
            was extended to the web server related commands (store, server) so
            they can be stored into a configuration file too.
            It is not required to type out the options in the command line all
            the time to store the analysis reports. With an example
            `store_cfg.json` config file like this:
            <pre>
    {
      "store":
        [
          "--name=run_name",
          "--tag=my_tag",
          "--url=http://codechecker.my/MyProduct"
        ]
    }
            </pre>
            The CodeChecker store command can be this short:
            <code>CodeChecker store reports --config store_cfg.json</code>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Other new features worth mentioning
            </template>
            <ul>
              <li>
                The review comments in the source code are shown by the
                <code>CodeChecker parse</code> command
              </li>
              <li>
                A free text description can be store to every run which can
                contain any compilation or analysis related description.
                <code>CodeChecker store --description "analysis related extra
                  information" ...</code>
              </li>
            </ul>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item color="green lighten-1">
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.11.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.11.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Show system comments for bugs
            </template>
            Review status changes by the users are automatically stored and
            shown at the report comment section for each report. With this
            feature the status changes of the reports can be easily tracked.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Introduce different compiler argument filtering if the original
              compiler was clang
            </template>
            If the original compiler used to build a project was clang/clang++
            only a minimal compilation flag filtering or modification is done.
            In the case where the original compiler was gcc/g++ many non
            compatible compiler flags were filtered which is not required if
            the original compiler is clang.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Store the Cppcheck plist reports
            </template>
            Plist reports generated by Cppcheck can be stored by the
            <code>CodeChecker store</code> command. For a more detailed example
            how to configure Cppcheck to generate the reports in the right
            format see the
            <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/docs/cppcheck.md">
              documentation
            </a>.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              CodeChecker config file support for the analysis arguments
            </template>
            The arguments for a <code>CodeChecker analyze</code> command can be
            given in a config file. A more detailed description about the usage
            and the config file format can be found
            <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/docs/analyzer/user_guide.md#analyzer-configuration-file">
              here
            </a>.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Log compile commands with absolute paths
            </template>
            With the introduction of a new environment variable
            (<b>CC_LOGGER_ABS_PATH</b>) the compiler include paths will be
            converted to an absoute path. This conversion can be necessary if
            the compiler command database created by CodeChecker will be used
            by other static analyzers (E.g. <i>Cppcheck</i>). For more
            information
            <a href="https://github.com/Ericsson/codechecker/blob/v6.11.0/analyzer/tools/build-logger#cc_logger_abs_path">
              see
            </a>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Enforce taking the analyzers from PATH
            </template>
            With the newly introduced environment variable
            (<b>CC_ANALYZERS_FROM_PATH</b>) the usage of the static analyzers
            in the PATH can be forced even if the configuration contains
            analyzers not from the PATH.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              List ClangSA checker options
            </template>
            The Clang Static Analyzer options can be listed now (requires
            clang v9.0.0 or newer). Use the command
            <code>CodeChecker analyzers --dump-config clangsa</code> to print
            the static analyzer configuration.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Support json output for parse command
            </template>
            The parse command can generate json output from the reports if
            required: <code>CodeChecker parse -e json analyzer_reports</code>.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Use CodeChecker parse with multiple directories
            </template>
            The <code>CodeChecker cmd parse</code> command now accepts multiple
            directories to parse the reports from.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Update the name of a run from the command line (CLI)
            </template>
            Allow the user to rename a run from command line.
            For more information
            <a href="https://github.com/Ericsson/codechecker/blob/dbd3feaffd389703a4c59c8d24b5f14f6d54374d/docs/web/user_guide.md#cmd-update">
              see
            </a>.
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star">
        <new-release-item>
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.10.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.10.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Filter results by bug path length
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  We are showing bug path length for each report at the Bug
                  overview page and now it is possible to filter run results
                  by bug path length on the GUI and at the command line too.
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
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.10.0/bug_path_length_filter.png"
                  alt="Bug path length filter"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item color="green lighten-1">
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.9.1"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.9.1 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Show macro definitions and notes
            </template>
            <v-row>
              <v-col cols="8">
                If a bug path goes through a macro, it is impossible to
                understand the bug path, since macro definitions cannot be
                resolved. Now we show macro expansion and notes in the web UI
                if your Clang version supports it.
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.9.1/macro_expansion.png"
                  alt="Macro expansion"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item>
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.9.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.9.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              New detection status types
            </template>
            <p>
              We added 2 new detection types:
              <ul>
                <li>
                  <b>Off</b> - were reported by a checker that is switched off
                  during the analysis.
                </li>
                <li>
                  <b>Unavailable</b> - were reported by a checker that does not
                  exists anymore because it was removed or renamed.
                </li>
              </ul>
            </p>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Disable review status change on the WEB UI
            </template>
            <p>
              We can disable review status change in the web UI for each
              product to force programmers to use inline source code comments.
            </p>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star" color="green lighten-1">
        <new-release-item color="green lighten-1">
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.8.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.8.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Filter results by report hash
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  We are showing report hash for each report at the Bug
                  overview page and now it is possible to filter run results
                  by report hash on the GUI and at the command line too.
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
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.8.0/report_hash_filter.png"
                  alt="Report hash filter"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              New filters at Checker statistics
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  We can get statistics only for specified runs, files,
                  checker names etc. using the filter bar beside the statistic
                  tables.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/statistics/checker_statistics.png"
                  alt="Checker statistics"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Delete filtered run results
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  It is possible to remove old, unneeded filtered reports by
                  clicking on the <i>Remove filtered reports</i> button at the
                  top of the filter bar.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/reports/remove_filtered_reports.png"
                  alt="Remove filtered reports"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Support managing source component on the GUI
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  Source components can be managed on the GUI at the Report
                  filter bar after clicking on the pencil icon at the
                  <i>Source component</i> filter. A pop-up window will be
                  opened where you can add, edit or remove existing source
                  components.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/reports/list_of_source_components.png"
                  alt="Manage source components"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Analysis Statistics
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  For each run the CodeChecker version (used to run the
                  analysis) and the static analyzer versions along with the
                  success/failure rate of the analysis can be viewed.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.8.0/analysis_statistics.png"
                  alt="Analysis statistics"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Fine gain control of Clang warnings
            </template>
            <p>
              Compiler warnings are diagnostic messages that report
              constructions that are not inherently erroneous but that are
              risky or suggest there may have been an error. You can
              fine-tune which warnings to use in the analysis by setting
              the enabled and disabled flags. These flags should start with
              a capital <b>W</b> or <b>Wno-</b> prefix followed by the
              warning name.
            </p>
            <b>Examples:</b>
            <ul>
              <li>
                <code>CodeChecker analyze /path/to/build.log -o /path/to/output/dir --enable Wunused --disable Wno-unused-parameter</code>
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Allow comparison of two report directories
            </template>
            <p>
              Now we are able to compare two report directories the same way
              as remote runs by using CodChecker command line.
            </p>
            <b>Examples:</b>
            <ul>
              <li>
                <code>CodeChecker cmd diff -b /path/to/report_dir_base -n /path/to/report_dir_new --new</code>
              </li>
            </ul>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              C/C++ standard auto detection
            </template>
            <p>
              Detect automatically which C/C++ standard was used for
              compilation by GCC and pass the relevant option to Clang
              (e.g. -std=c++11). This way the same standard version is used
              during analysis as the one in the build system even if it wasn't
              set explicitly.
            </p>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>

      <v-timeline-item fill-dot icon="mdi-star">
        <new-release-item>
          <template v-slot:title>
            <a
              href="https://github.com/Ericsson/codechecker/releases/tag/v6.7.0"
              target="_blank"
              class="white--text"
            >
              Highlights of CodeChecker 6.7.0 release
            </a>
          </template>

          <new-feature-item>
            <template v-slot:title>
              Component filters
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  Aministrators of a product can create new source components
                  by using <b>CodeChecker cmd components</b> subcommand which
                  can be used to filter results by multiple file paths.
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
                <a href="https://github.com/Ericsson/codechecker/blob/master/docs/user_guide.md#source-components">
                  see
                </a>.
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.7.0/component_filter.png"
                  alt="Component filter"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Diff two different tagged versions of the same run
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  It is possible to compare two different tagged versions of
                  the same run not only different run names.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/reports/compare_tags.png"
                  alt="Diff tagged versions of the same run"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Generate index.html file by using PlistToHTML
            </template>
            <v-row>
              <v-col cols="8">
                <p>
                  Creating an index.html file that lists the found reports
                  which links to the local html pages.
                  <b>Examples:</b>
                  <ul>
                    <li>
                      <code>CodeChecker parse ./reports -e html -o ./reports_html</code>
                    </li>
                  </ul>
                  For more information
                  <a href="https://github.com/Ericsson/codechecker/blob/master/docs/usage.md#step-3">
                    see
                  </a>.
                </p>
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/new_features/6.7.0/plist_to_html_index.png"
                  alt="Plist to html"
                  width="100%"
                >
              </v-col>
            </v-row>
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Separate filter options for cmd line
            </template>
            <p>
              Create separate filter options for <b>CodeChecker cmd results</b>
              and <b>CodeChecker cmd diff</b> command line options to be more
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
            <a href="https://github.com/Ericsson/codechecker/blob/master/docs/user_guide.md#cmd">
              see
            </a>.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Enable passwordless token based authentication
            </template>
            <p>
              Command line clients can authenticate using the username/password
              stored in the <b>.codechecker.passwords.json</b>. It is obviously
              not a good idea to store passwords in text files. Instead of this
              the user is able to generate a token from command line, that can
              be used to authenticate in the name of his/her name.
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
            <a href="https://github.com/Ericsson/codechecker/blob/master/docs/authentication.md#personal-access-token">
              see
            </a>.
          </new-feature-item>

          <new-feature-item>
            <template v-slot:title>
              Consistent report counting
            </template>
            <ul>
              <li>
                Uniqueing is disabled at bug list view by default.
              </li>
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
                    Detection status: <b>New</b>, <b>Reopened</b>, <b>Unresolved</b>
                  </li>
                </ul>
              </li>
            </ul>
          </new-feature-item>
        </new-release-item>
      </v-timeline-item>
    </v-timeline>
  </v-container>
</template>

<script>
import { NewFeatureItem, NewReleaseItem } from "@/components/NewFeatures";

export default {
  name: "NewFeatures",
  components: {
    NewFeatureItem,
    NewReleaseItem
  }
};
</script>
