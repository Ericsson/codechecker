This directory contains a set of sample SARIF files that illustrate various "exceptional conditions", for example:

- A log file contains no runs.
- A run failed with an error-level "tool execution notification".
- A run contains no results.

Developers of applications (such as viewers or bug filing systems) that consume SARIF log files can use the files in this directory to ensure that their application behaves properly under all these conditions.