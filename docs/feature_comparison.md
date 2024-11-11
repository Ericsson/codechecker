Feature comparison
==================

CodeChecker includes two user interfaces, which support different actions. This
comparison summary is intended to overview which feature is available through
which interface.

Table of Contents
-----------------

* [Analysis invocation](#analysis-invocation)
* [Storage of reports to a server](#storage-of-reports-to-a-server)
* [Report navigation and visualisation](#report-navigation-and-visualisation)
    * [Report management, triaging tools](#report-management-triaging-tools)
    * [Statistics, summary views](#statistics-summary-views)
* [Run management](#run-management)
* [Server administration](#server-administration)
    * [Starting a server](#starting-a-server)
    * [Product management](#product-management)
    * [Authentication and access control](#authentication-and-access-control)

# Analysis invocation

* Analyzers can only be invoked through the command-line command,
[`analyze`](analyzer/user_guide.md#analyze).

* Analysis runs locally on the user's computer.

* Cross&ndash;Translation-Unit analysis supported if using a [Clang version
which supports it](http://github.com/Ericsson/clang).

# Storage of reports to a server

* Storage of reports can only be done through the command-line command,
[`store`](web/user_guide.md#store).

# Report navigation and visualisation

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Listing basic (file, check message, ...) report summary| ✓ | ✓ |
| Listing advanced (detection status, review, ...) report summary | ✗ | ✓ |
| Basic (file path, check name, ...) filtering of reports | ✓ | ✓ |
| Advanced (detection status, detection date, ...) filtering | ✗ | ✓ |
| Printing bug path for report | [Only for local output folder](analyzer/user_guide.md#parse) | ✓ |
| Visualisation of bug path in the code | [Only through exporting to HTML](analyzer/user_guide.md#parse) | ✓ |
| Listing reports in the same file | Only through filters | ✓ |
| Listing all reports in a product | ✗ | ✓ |

## Report management, triaging tools

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Showing comments for a particular report | ✗ | ✓ |
| Commenting on reports | ✗ | ✓ |
| Comment management (edit, delete) | ✗ | ✓ |
| Showing review status of a report | ✗ | ✓ |
| Changing review status of a report | ✗ | ✓ |
| *(Legacy)* Importing [suppressions](web/user_guide.md#manage-suppressions) of `< 6.0` CodeChecker | ✓ | ✗ |
| Difference of two runs | ✓ | ✓ |
| Difference of a stored run to a local output folder | ✓ | ✗ |

## Statistics, summary views

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Run overview | Basic (only report count and timestamp) | ✓ |
| Breakdown of reports per run, per check | ✓ | ✓ |
| Exporting report breakdown to CSV | ✓ | ✓ |

# Run management

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Listing runs in a product | ✓ | ✓ |
| Listing store actions to a run (history) | ✗ | ✓ |
| Deleting runs | ✓ | ✓ |

# Server administration

## Starting a server

The command-line command [`CodeChecker server`](web/user_guide.md#server) is
used to start a CodeChecker server.

This command is also responsible for handling schema upgrades.

## [Product management](web/products.md)

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Listing products on a server | ✓ | ✓ |
| Addition, modification and removal of products | ✓ | ✓ |

## [Authentication](web/authentication.md) and [access control](web/permissions.md)

| Feature name | [Command-line](web/user_guide.md#cmd) | [Web GUI](/www/userguide/userguide.md) |
|--------------|-----------------------------------------|----------------------------------------|
| Configuration of authentication system | Through configuration file | ✗ |
| Managing permissions granted to users | ✗ | ✓ |
