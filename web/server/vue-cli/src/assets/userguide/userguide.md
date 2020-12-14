User Guide
==========

**CodeChecker** is a static analysis infrastructure built on the [LLVM/Clang
Static Analyzer](http://clang-analyzer.llvm.org) toolchain, alternative tool for
[`scan-build`](http://clang-analyzer.llvm.org/scan-build.html) in a Linux or
macOS (OS X) development environment.

<div class="github">More descriptions and guides available
<a href="https://github.com/Ericsson/codechecker/blob/master/README.md">
on GitHub</a>
</div>

Table of Contents
=================

* [Products](#userguide-products)
  * [Managing products](#userguide-managing-products)
    * [Disable review status change](#userguide-disable-review-status-change)
    * [Remove a product](#userguide-remove-product)
  * [Managing permissions](#userguide-managing-permissions)
* [List of runs](#userguide-list-of-runs)
  * [Filter runs](#userguide-filter-runs)
  * [Compare runs](#userguide-compare-runs)
  * [Delete runs](#userguide-delete-runs)
  * [Sorting runs](#userguide-sorting-runs)
* [Checker statistics](#userguide-checker-statistics)
  * [Filtering statistics](#userguide-filter-statistics)
  * [Uniqueing checker statistics](#userguide-checker-statistics-uniqueing)
* [Analysis results](#userguide-analysis-results)
  * [Filtering](#userguide-filtering)
    * [Remove filtered reports](#userguide-remove-filtered-reports)
    * [Clear report filters](#userguide-clear-report-filters)
    * [Unique reports](#userguide-unique-reports)
  * [Diff mode](#userguide-diff-mode)
    * [Compare two different runs](#userguide-diff-runs)
    * [Compare two different tagged versions of the same](#userguide-diff-tags)
  * [Review status](#userguide-review-status)
  * [Detection status](#userguide-detection-status)
  * [Severity levels](#userguide-severity-levels)
  * [Manage source components](#userguide-manage-source-components)
* [Bug view](#userguide-bug-view)
  * [Report navigation tree](#userguide-report-navigation-tree)
  * [Button pane](#userguide-button-pane)
     * [Show documentation](#userguide-show-documentation)
     * [Change review status](#userguide-change-review-status)
  * [Same reports](#userguide-same-reports)
  * [Bug path view](#userguide-bug-path-view)
  * [Comment](#userguide-comment)
* [Run history](#userguide-run-history)
* [Server configuration](#userguide-server-config)
  * [Notification banner](#userguide-notification)

# <a name="userguide-user-guide"></a> Products
The product system allows a single CodeChecker server to serve multiple separate
result databases, named "products", under the same IP address and authentication
domain.

## <a name="userguide-managing-products"></a> Managing products
![Products](images/products.png)

Click *Add new product*, then fill the form presented. The values that need to
be filled here are the same as the arguments for
`CodeChecker cmd products add`. These buttons are visible only for
*Super Users*.

![New product](images/new_product.png)

If the product creation is successful, the window will disappear and the
product will appear in the product list.

Editing a product is done through the pencil icon. This window lets you edit
the product's configuration.

![Edit product](images/edit_product.png)

### <a name="userguide-disable-review-status-change"></a> Disable review status change
Review status change can be disabled on the WEB UI to force programmers to use
inline source code comments. This can be configured on the product editing
window by administrators of a product.

### <a name="userguide-remove-product"></a> Remove a product
Products can be deleted by clicking on the red trash bin. This way the product
is only unmounted from the server (losing access control data and connection),
but **no analysis results are deleted**.

![Remove product](images/remove_product.png)

## <a name="userguide-managing-permissions"></a> Managing permissions
* Server-wide permissions can be edited by clicking *Edit global permissions*.
* Product-level permissions can be edited by clicking the edit icon for the
product you want to configure the permissions.

The two lists show the users and groups known to the system - if a tick is
present in its row, the given user or group has the permission directly
granted. (Users who only have a certain permission through permission
inheritance are not shown with a tick.)

![Product permissions](images/product_permissions.png)

Only the permissions you have rights to manage are shown.

You can edit multiple permissions opening the window only once. Simply tick or
untick the users/groups you want to give the permission to or revoke from them.
Clicking *OK* will save the changes to the database.

# <a name="userguide-list-of-runs"></a> List of runs
List page contains the analysis runs available on the server under the selected
product.

You can do the following on this page:
- [Filter runs](#userguide-filtering).
- [Compare analysis](#userguide-compare-runs).
- [Delete runs](#userguide-delete-runs).
- [Sorting runs](#userguide-sorting-runs).

![Runs](images/runs.png)


The meaning of the table columns:
- **Diff** - In this column you can select two runs (*baseline* and
*compared to*) which will be compared to each other by click on the *Diff*
button.
- **Name** - Name of the run.
- **Number of unresolved reports** - Number of non unique reports excluding
*Resolved*, *False positive* and *Intentional* reports.
- **Storage date** - Storage date of the runs.
- **Analysis duration** - Duration of the analysis.
- **Check command** - By clicking on *Show* text the check command will be shown
in a pop-up window.
- **Detection status** - Detection statuses are calculated based on the detection
status values from the previous store where the reports are stored again with
the same run name. When storing the results of a run from scratch then each
report will have detection status of *New*.
- **Version tag** - Latest version tag of the run.
- **Delete** - In this column you can select multiple runs which will be removed
by clicking on the *Delete* button.

## <a name="userguide-filter-runs"></a> Filter runs
You can filter runs by run name using the input box above the run list table.
The filter is **case insensitive** and doing a **substring matching**. If we
start typing some phrase in this input box, the list are being _filtered
automatically_. 

## <a name="userguide-compare-runs"></a> Compare runs
Calculates difference between two analyses of the project, showing which bugs
have been fixed and which are newly introduced.

## <a name="userguide-delete-runs"></a> Delete runs
You can delete multiple runs by selecting them and clicking on the Delete
button. It will remove the run and all related data from the database.

## <a name="userguide-sorting-runs"></a> Sorting runs
It is possible to change the order of the runs by clicking on a cell at header
of the run list table. For example, you can sort the run list by the number of
bugs or the run name.

# <a name="userguide-checker-statistics"></a> Checker statistics
A statistical overview can be seen under "Checker statistics" panel.
Here you can see multiple tables: 
- **Checker statistics** table shows the number of reports by checkers based on
some attributes of the report like severity, and report status.
- **Severity statistics** table shows the number of report by severity levels.


![Checker statistics](images/checker_statistics.png)

## <a name="userguide-filter-statistics"></a> Filtering statistics
We can get statistics only for specified runs, files, checker names etc. by
using the filter bar beside the statistic tables. For more information check
the report filtering [section](#userguide-filtering).

## <a name="userguide-checker-statistics-uniqueing"></a> Uniqueing checker statistics
The same bug may appear several times if it is found on different execution
paths, i.e. through different function calls. By checking **Unique reports** a
report appears only once even if it is found on several paths. By default
uniqueing is enabled for statistics.

# <a name="userguide-analysis-results"></a> Analysis results
If you select a run at the [list of runs](#userguide-list-of-runs) view, you get
to this page. This page lists the analysis result for the given run.

![Reports](images/reports.png)

## <a name="userguide-filtering"></a> Filtering
When opening the bug list view under "All reports" tab or by clicking a specific
run or by opening "diff view" between two runs then the following filter options
are available:
- [**Unique reports**](#userguide-unique-reports) - You can uniqueing the
reports by checking this.
- **Report hash** - Every report has a unique (hash) identifier called Report
Identifier (RI) which can be filtered by using this input box.
- **Baseline**
  - **Run name** - You can select one or more run names. The result list is
restricted on the findings in these runs. By selecting a specific run in the
"runs" view this field is filled by default. In "All reports" tab no run is
selected in which case the reports from all runs are visible.
  - **Run tag** - When runs are stored in update mode (i.e. on the same run
name), then the specific runs can be tagged in order to be easier to identify
them. By this field you can select the reports found during a specific run
event.
- [**Compare to**](#userguide-diff-mode)
  - **Run name** - Here you can select multiple run name which you want to
compare against the baseline filter set.
  - **Run tag** - Here you can select multiple run tags which you want to
compare against the baseline filter set.
  - **Diff type** - Here you can set if you'd like to see the bugs which appear
only in the **Baseline**, **Compare to** or both.
- [**Review status**](#userguide-review-status) - You can select the reports
with the given review status to check only *False positive*, *Unreviewed*, etc.
reports.
- [**Detection status**](#userguide-detection-status) - You can select the
reports with the given detection status to check only *Unresolved*, *Resolved*,
etc. reports.
- [**Severity**](#userguide-severity-levels) - The nature of the bugs is sorted
in different severity levels. For example, a division by zero or a null pointer
dereference is more serious than an unused variable. By this field you can
select the reports on the given severity levels.
- **Bug path length** - A bug path length interval can restrict the list of
displayed bug reports. In these fields you can choose the minimum and maximum
values of bug path length.
- **Detection date** - A date interval can also restrict the list of displayed
bug reports. In this field you can choose the date of detection or fixing.
- **File path**: You can choose a set of files to restrict the list of bug
reports.
- [**Source component**](https://github.com/Ericsson/codechecker/blob/master/docs/web/user_guide.md#source-components) -
Here you can select multiple source components which are named collection of
directories specified as directory filter.
- **Checker name** - If you are interested in specific type of bugs then here
you can choose them.
- **Checker message** - The static analysis tools provide a message to indicate
the reason of a specific bug. This message is also filterable.

Run name may contain `*` quantifiers which matches any number of characters
(zero or more). So if you have `run_1_a_name`, `run_2_b_name`, `run_2_c_name`,
`run_3_d_name` then `run_2*` will select `run_2_b_name` and `run_2_c_name`.

When you select a filter option on any field then a number indicates on the
right side of the option the number of reports which belong to that specific
option. If the report count could not be determined this value will be *N/A*.

### <a name="userguide-remove-filtered-reports"></a>Remove filtered reports
Filtered reports can be removed by clicking on the **Remove filtered reports**
button at the bottom of the filter bar.

**!!!WARNING!!!** Once you have removed filtered reports it can not be undone.
Please make sure that you want to remove all filtered results before clicking
on this button.

![Remove filtered reports](images/remove_filtered_reports.png)

### <a name="userguide-clear-report-filters"></a>Clear report filters
Filter options can be cleared separately by clicking on the trash icon beside
a filter or all filters can be cleared by using *Clear All Filters* button at
the top of the filter bar.

![Clear all filters](images/clear_all_filters.png)

![Clear report filters](images/clear_report_filters.png)

### <a name="userguide-unique-reports"></a> Unique reports
At the top of the filter panel there is a "Unique reports" checkbox. This
narrows the report list to unique bug. The same bug may appear several times if
it is found on different control paths, i.e. through different function calls or
in multiple runs. By checking "Unique reports" a report appears only once even
if it is found on several paths.

![Unique reports](images/unqiue_reports.png)

## <a name="userguide-diff-mode"></a> Diff mode
In diff mode you can calculate the difference between multiple analyses of the
project, showing which bugs have been fixed and which are newly introduced or
which can be fined in all runs.

At the **Baseline** filter section you can select the run names and run tags
against which you want to check the difference.

At the **Compare to** filter section you can select the run names and run tags
which you want to compare against the *Baseline* runs and run tags.

### <a name="userguide-diff-runs"></a> Compare two different runs
![Compare two different runs](images/run_diff.png)

### <a name="userguide-diff-tags"></a> Compare two different tagged versions of the same
![Compare two different tagged versions of the same](images/run_tag_diff.png)

## <a name="userguide-review-status"></a> Review status
Reports can be assigned a review status of the following values:
- <span class="customIcon review-status-unreviewed"></span> **Unreviewed**
(_default_): Nobody has seen this report.
- <span class="customIcon review-status-confirmed"></span> **Confirmed**:
This is really a bug.
- <span class="customIcon review-status-false-positive"></span>
**False positive**: This is not a bug. Before marking a bug false positive
you should read the [false positive how to](https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/false_positives.md).
- <span class="customIcon review-status-intentional"></span> **Intentional**:
This report is a bug but we don't want to fix it.

Review statuses are connected to
[report hashes](https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/report_identification.md).
If the same report can be found in multiple runs it will have the same review
status.

It can be changed on the [GUI](#userguide-change-review-status) or by using
[source code comments ](https://github.com/Ericsson/codechecker/blob/master/docs/analyzer/user_guide.md#source-code-comments)
(*codechecker_false_positive*, *codechecker_confirmed*, etc.)

**Note**: source code comment is stronger and can overwrite the value in the
database.

## <a name="userguide-detection-status"></a> Detection status
The detection status is the state of a bug report in a run.

- The detection status of a report is connected to the **report ID**. It means
that every report has a separate detection status.
- It will be *calculated automatically* by the server on run storage events.
- Changing the review status by using source code comments will not affect
the detection status change.

When storing the results of a run from scratch then each report has
detection status <span class="customIcon detection-status-new"></span> **New**.
When the reports stored again with the same run name then the detection status
can change to one of the following options:
- <span class="customIcon detection-status-resolved"></span> **Resolved**: when
the bug report can't be found after the subsequent storage.
- <span class="customIcon detection-status-unresolved"></span> **Unresolved**:
when the bug report is still among the results after the subsequent storage.
- <span class="customIcon detection-status-reopened"></span> **Reopened**: when
a resolved bug appears again.
- <span class="customIcon detection-status-off"></span> **Off**: were reported
by a checker that is switched off during the last analysis which results were
stored.
- <span class="customIcon detection-status-unavailable"></span> **Unavailable**:
were reported by a checker that does not exists anymore because it was removed
or renamed.

The diagram below shows the detection status transition which may happen when
storing results to the server. For example if the detection status of a report
in the database is **New** the server will change it to **Unresolved**,
**Resolved**, **Off** or **Unavailable** based on the conditions above.

![Detection status change](images/detection_status_flow_chart.png)

## <a name="userguide-severity-levels"></a> Severity levels
We are mapping checker names to different severity levels:
- <span class="customIcon icon-severity-unspecified"></span> **Unspecified**
- <span class="customIcon icon-severity-style"></span> **Style**:
(E.g. _modernize-raw-string-literal, modernize-use-auto, etc._)
- <span class="customIcon icon-severity-low"></span> **Low**
(E.g. _deadcode.DeadStores, misc-unused-parameters, etc._)
- <span class="customIcon icon-severity-medium"></span> **Medium**:
(E.g. _unix.Malloc, core.uninitialized.Assign, etc._)
- <span class="customIcon icon-severity-high"></span> **High**:
(E.g. _core.DivideZero, core.NullDereference, cplusplus.NewDelete, etc._)
- <span class="customIcon icon-severity-critical"></span> **Critical**

## <a name="userguide-manage-source-components"></a> Manage source components
Source components are named collections of directory filters. Source components
can be managed only by administrators after clicking on the pencil icon at the
Source component filter.

![Manage source components](images/manage_source_components.png)

A pop-up window will be opened where you can add, edit or remove existing
source components.

![List of source components](images/list_of_source_components.png)

# <a name="userguide-bug-view"></a> Bug view
At this page you can navigate between reports and check the errors what
CodeChecker found.

This page has four main parts:
- [Report navigation tree](#userguide-report-navigation-tree)
- [Button pane](#userguide-button-pane)
- [Bug path view](#userguide-bug-path-view)
- [Comments](#userguide-comment)

![Report view](images/report_view.png)

## <a name="userguide-report-navigation-tree"></a> Report navigation tree
Report Navigation Tree shows the found reports at the currently opened file. The
reports are grouped by the severity level.
You can navigate between them by clicking on a node in the tree.

![Report navigation tree](images/report_navigation_tree.png)

## <a name="userguide-button-pane"></a> Button pane
Button Pane contains several items which help you to change or get some
property of the currently opened report. 
![Button pane](images/button_pane.png)

### <a name="userguide-show-documentation"></a> Show documentation
Show Documentation button shows the documentation of the actual checker which
identified by the currently opened report.
![Checker documentation](images/checker_documentation.png)

### <a name="userguide-change-review-status"></a> Change review status
Reports can be assigned a review status of *Unreviewed*, *Confirmed*, *False
positive*, *Intentional*, along with an optional comment on why this status was
applied. We can change the review status from the default
<span class="customIcon review-status-unreviewed"></span> _Unreviewed_ option
to something else in the report details view above the file view.

![Unreviewed](images/review_status_unreviewed.png)

If you changed the review status, you can optionally explain the reason why
you changed it.
![Change review status](images/review_status_change.png)

If somebody has already changed the review status from the default one, you can
see extra information (who changed the review status, when and why) beside
the review status selector by hovering on the message icon. This message icon is
hidden by default if nobody has changed the review status.
![Review status message](images/review_status_message.png)

## <a name="userguide-same-reports"></a> Same reports
Several reports may belong to a specific bug if the but itself can be reached on
different control paths. In the Bug viewer you can check whether the selected
bug is available on a different path.

![Same reports](images/same_reports.png)

## <a name="userguide-bug-path-view"></a> Bug path view
Some checkers are able to follow the execution path along the control flow of
the program. If a bug appears on any of these paths, then CodeChecker is able to
present the full path on which this so called symbolic execution reached the
place of error. This path can be checked in this bug path view.

![Bug path](images/bug_path.png)

## <a name="userguide-comment"></a> Comment
Bug reports can be commented. You can add new comments,
edit (<span class="customIcon edit" style="padding:0px"></span>) and
delete (<span class="customIcon delete" style="padding:0px"></span>) them.

The author of the comment will be the currently logged in user. If the user is
not logged in, the author of the comment will be _Anonymous_.

Comments are shown for the same report found in multiple runs.

![Comment](images/comment.png)

# <a name="userguide-run-history"></a> Run history
When selecting a run then a "Run history" tab appears next to the
*Bug overview*. In this window you can check the specific run events which
happened during a storage process under the same run name. This way you can list
the reports' state in the selected run event.

![Run history](images/run_history.png)

# <a name="userguide-server-config"></a> Server Configuration
## <a name="userguide-notification"></a> Global Notification banner
There is an option to set a global notification text, that will show on top of
every page over the CodeChecker logo. For every connecting client. 

![Notification](images/notification.png)

You can edit this alert on the products page with "Edit announcement" button,
but **Super User** permissions are necessary.

![Products](images/products.png)

You can remove the current notification by saving an empty text.

![Notification Dialog](images/notificaiton_dialog.png)
