# statistics-collector
`statistics-collector` is a Python tool which helps you to process statistical
results of the Clang analyzer. It contains a script called `post-process-stats`
which will read the Clang analyzer outputs where the statistics emitter
checkers were enabled and collect the statistics into a special yaml file which
can be parsed by statistics checkers.

## Install guide
```sh
# Create a Python virtualenv and set it as your environment.
make venv
source $PWD/venv/bin/activate

# Build and install plist-to-html package.
make package
```

## Usage
<details>
  <summary>
    <i>$ <b>post-process-stats --help</b> (click to expand)</i>
  </summary>

```
usage: post-process-stats [-h] -i folder
                          [--stats-min-sample-count STATS_MIN_SAMPLE_COUNT]
                          [--stats-relevance-threshold STATS_RELEVANCE_THRESHOLD]
                          [-v]
                          output_dir

Collect statistics from the clang analyzer output.

positional arguments:
  output_dir            Output directory where the statistics yaml files will
                        be stored into.

optional arguments:
  -h, --help            show this help message and exit
  -i folder, --input folder
                        Folder which contains statistical results of clang to
                        collect statistics.
  --stats-min-sample-count STATS_MIN_SAMPLE_COUNT
                        Minimum number of samples (function call occurrences)
                        to be collected for a statistics to be relevant '<MIN-
                        SAMPLE-COUNT>'.
  --stats-relevance-threshold STATS_RELEVANCE_THRESHOLD
                        The minimum ratio of calls of function f that must
                        have a certain property property to consider it true
                        for that function (calculated as calls with a
                        property/all calls). CodeChecker will warn for calls
                        of f do not have that property.
                        '<RELEVANCE_THRESHOLD>'.
  -v, --verbose         Set verbosity level.

Example:
  post-process-stats -i /path/to/pre_processed_stats /path/to/stats
```
</details>

## License

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.