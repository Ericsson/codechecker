# Log configuration

# Command line

Command line flag can be used to turn in CodeChecker debug mode. The different
subcommands can be given a `-v` flag which needs a parameter. Possible values
are `debug`, `debug_analyzer` and `info`. Default is `info`.

`debug_analyzer` switches analyzer related logs on:

```sh
CodeChecker check <name> -b <build_command> --verbose debug_analyzer
```

Turning on CodeChecker debug level logging is possible for the most
subcommands:

```sh
CodeChecker check <name> -b <build_command> --verbose debug
CodeChecker server -v <view_port> --verbose debug
```

# Change log configuration for the server

The log level for a server can be changed in two ways.

## 1. At the server start

Debug log can be enabled like this at the server start.
```
Codechecker server ... --verbose debug
```

The log levels can not be changed after the server was started.

## 2. While the server is running

The log configuration can be changed for a running server if it was started
in an environment where the `CC_LOG_CONFIG_PORT` environment variable is set.

```sh
CC_LOG_CONFIG_PORT='8888' Codechecker server ...
```
The running server will accept log configurations on the configured `8888` port.
This way the log configuration can be changed without a server restart.

### Sending new configuration to a running server

Sending a new configuration to the server can be done easily with
`scripts/send_log_config.py` like this:
```
./send_log_config.py -c new_log_cfg.conf -p 8888
```

Sending a configuration can be done only on the same machine where the server was started. See further
details [here](https://docs.python.org/2/library/logging.config.html#logging.config.listen).

# Example debug log configuration with multiple handlers

For more information see: [logging-cookbook](https://docs.python.org/2/howto/logging-cookbook.html) or
[logging.config](https://docs.python.org/2/library/logging.config.html)

```json
{
  "version": 1,
  "disable_existing_loggers": true,
  "formatters": {
    "brief": {
      "format": "[%(asctime)s] - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M"
    },
    "precise": {
      "format": "[%(asctime)s] {%(name)s} [%(process)d] <%(thread)d> - %(filename)s:%(lineno)d %(funcName)s() - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S"
    }
  },
  "loggers": {
    "analyzer": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    },
    "analyzer.tidy": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    },
    "analyzer.clangsa": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    },
    "server": {
      "level": "DEBUG",
      "handlers": [ "console", "file" , "daily_log"]
    },
    "buildlogger": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    },
    "report": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    },
    "system": {
      "level": "DEBUG",
      "handlers": [ "console", "file", "daily_log" ]
    },
    "profiler": {
      "level": "DEBUG",
      "handlers": [ "console", "file" ]
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
      "formatter": "brief",
      "stream": "ext://sys.stdout"
    },
    "file": {
      "class": "logging.handlers.RotatingFileHandler",
      "formatter": "precise",
      "level": "DEBUG",
      "filename": "file.log",
      "encoding": "utf-8",
      "maxBytes": 1000000,
      "backupCount": 3
    },
    "daily_log": {
      "class": "logging.handlers.TimedRotatingFileHandler",
      "formatter": "precise",
      "level": "DEBUG",
      "filename": "daily.log",
      "encoding": "utf-8",
      "when": "D",
      "interval": 1
    }
  }
}
```
