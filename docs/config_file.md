# CodeChecker configuration file
CodeChecker allows the configuration from explicit configuration files for
multiple commands through the `--config` option:

- `CodeChecker analyze`
- `CodeChecker check`
- `CodeChecker parse`
- `CodeChecker server`
- `CodeChecker store`
- `CodeChecker cmd` actions that connect to a server or product

Set `CC_CONFIG_FILE` to use a configuration file without passing `--config`
each time:

```sh
export CC_CONFIG_FILE="$HOME/.codechecker/codechecker.json"
CodeChecker store ./reports -n myproject
CodeChecker cmd runs
```

An explicit `--config FILE` (or `--config=FILE`) selects that file instead of
`CC_CONFIG_FILE`. A selected file must exist. No configuration file is loaded
automatically when neither is set.

Options from `CC_CONFIG_FILE` are appended to the command line, so they take
precedence over earlier scalar options. An explicit `--config` is expanded at
its position in the command line; options after it can override scalar values
from the file. Repeatable options retain their normal command-line behavior.

For `cmd`, nest configuration by action name, including any intermediate
subcommands. For example:

```json
{
  "store": ["--url=https://codechecker.example.com:9090/MyProduct"],
  "cmd": {
    "runs": ["--url=https://codechecker.example.com:9090/MyProduct"],
    "results": ["--url=https://codechecker.example.com:9090/MyProduct"],
    "login": ["--url=https://codechecker.example.com:9090"],
    "products": {
      "list": ["--url=https://codechecker.example.com:9090"]
    }
  }
}
```

Product actions and `store` require a product URL including its endpoint.
Server actions such as `login` and `products list` require a server URL.
CodeChecker passes these URLs through unchanged; it does not derive one from
the other. The same nesting is supported in YAML. Actions without a matching
section keep their normal defaults. Use `--config` after the action name, for
example `CodeChecker cmd products list --config codechecker.json`.

Configuration options are expanded as command-line arguments as described
above.

For example if you run the following command:

```sh
CodeChecker analyze compilation.json -o ./reports --config ./codechecker.json
```

then the analyzer parameters from the
[`codechecker.json`](https://github.com/Ericsson/codechecker/blob/master/config/config_files/codechecker.json) configuration
file will be emplaced as command line arguments:

```sh
CodeChecker analyze \
  compilation.json \
  -o ./reports \
  --enable=core.DivideZero \
  --enable=core.CallAndMessage \
  --analyzer-config clangsa:unroll-loops=true \
  --checker-config clang-tidy:google-readability-function-size.StatementThreshold=100 \
  --report-hash context-free-v2 \
  --verbose debug \
  --clean
```

For supported configuration file formats please read the sections below.

You can use any **environment variable** inside this file (e.g: `$HOME`,
`$USER`) and it will be expanded:
`{ "analyze": [ "--skip=$HOME/project/skip.txt" ] }`

> Note: If the configuration file doesn't have an extension, to be backward
compatible with old releases the default will be JSON. We recommend to use
explicit extensions for configuration files (e.g.: `json`, `yaml`, etc.).


# JSON
The format of JSON configuration file looks like this:
```json
{
  "analyze": [
    "--enable=core.DivideZero",
    "--enable=core.CallAndMessage",
    "--analyzer-config",
    "clangsa:unroll-loops=true",
    "--checker-config",
    "clang-tidy:google-readability-function-size.StatementThreshold=100",
    "--report-hash", "context-free-v2",
    "--verbose=debug",
    "--clean"
  ],
  "parse": [
    "--trim-path-prefix",
    "$HOME/workspace"
  ],
  "server": [
    "--workspace=$HOME/workspace",
    "--port=9090"
  ],
  "store": [
    "--name=run_name",
    "--tag=my_tag",
    "--url=http://codechecker.my:9090/MyProduct"
  ]
}
```

These configuration files must have extension `json`.

Options which require parameters have to be in either of the following formats:

- Use equal sign to separate option and parameter in quotes:
  `{ "analyze": [ "--verbose=debug" ] }`
- Use separated values for option and parameter:
  `{ "analyze": [ "--verbose", "debug" ] }`

> Note: The limitation of this format is that you can't write comments in this
file. If you would like to leave comments (e.g.: why you enabled a checker or
an option) please use [YAML](#yaml) format.

# YAML
The format of YAML configuration file looks like this:
```yaml
analyzer:
  # Enable/disable checkers.
  - --enable=core.DivideZero
  - --enable=core.CallAndMessage
  # Analyzer configurations.
  - --analyzer-config=clangsa:unroll-loops=true
  - --checker-config=clang-tidy:google-readability-function-size.StatementThreshold=100
  # Optional options.
  - --report-hash=context-free-v2
  - --verbose=debug
  - --clean

parse:
  - --trim-path-prefix=$HOME/workspace

server:
  - --workspace=$HOME/workspace"
  - --port=9090"

store:
  - --name=run_name
  - --tag=my_tag
  - --url=http://codechecker.my:9090/MyProduct
```

These configuration files must have extension `yml` or `yaml`.
