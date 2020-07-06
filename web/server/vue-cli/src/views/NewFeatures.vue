<template>
  <!-- eslint-disable max-len -->
  <v-container fluid>
    <v-timeline align-top>
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
                  src="@/assets/userguide/images/bug_path_length_filter.png"
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
                  src="@/assets/userguide/images/macro_expansion.png"
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
                  src="@/assets/userguide/images/report_hash_filter.png"
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
                  src="@/assets/userguide/images/checker_statistics.png"
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
                  src="@/assets/userguide/images/remove_filtered_reports.png"
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
                  src="@/assets/userguide/images/list_of_source_components.png"
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
                  src="@/assets/userguide/images/analysis_statistics.png"
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
            <v-row>
              <v-col cols="8">
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
              </v-col>
              <v-col>
                <img
                  src="@/assets/userguide/images/analysis_statistics.png"
                  alt="Analysis statistics"
                  width="100%"
                >
              </v-col>
            </v-row>
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
                  src="@/assets/userguide/images/component_filter.png"
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
                  src="@/assets/userguide/images/run_tag_diff.png"
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
                  src="@/assets/userguide/images/plist_to_html_index.png"
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
