# CodeChecker Memory Safety Reporter

A tool to collect all important information about a given analyzation.
The tool collects the reports from the run in sarif format, the metadata,
all the settings for all the checkers set at the time of the run and
the passed setting to CodeChecker then it creates an archive in either
zip or tar.gz format.

## Usage

The tool needs only the report directory to run but other optional arguments can also be used.

Running the tool: `memory-safety-reporter -o MemorySafetyReport -r /path/to/report/directory`

For the extensive list of argument, see the help of the script!

## Requirements

- Python >= 3.9

## Authors

CodeChecker Team (Ericsson)
