
## Report hash generation module
Multiple hash types are available:
- [`CONTEXT_FREE`](#generate-path-sensitive-report-hash)
- [`PATH_SENSITIVE`](#generate-context-sensitive-report-hash)

You can use this library to generate report hash for these types by using the
`get_report_hash` function.

### Generate path sensitive report hash
`get_report_hash` function can be used to generate report hash with bug path
if the hash type parameter is `PATH_SENSITIVE`.

High level overview of the hash content:
* `file_name` from the main diag section.
* `checker name`.
* `checker message`.
* `line content` from the source file if can be read up.
* `column numbers` from the *main diag section*.
* `range column numbers` only from the control diag sections if column number
  in the range is not the same as the previous control diag section number in
  the bug path. If there are no control sections event section column numbers
  are used.

*Note*: as the *main diagnostic section* the last element from the bug path is
used.

### Generate context sensitive report hash
`get_report_hash` function can be used to generate report hash without bug path
if the hash type parameter is `CONTEXT_FREE`.

High level overview of the hash content:
* `file_name` from the main diag section.
* `checker message`.
* `line content` from the source file if can be read up. All the whitespaces
  from the source content are removed.
* `column numbers` from the main diag sections location.

### Generate path hash
`get_report_path_hash` can be used to get path hash for the given bug path
which can be used to filter deduplications of multiple reports.

## License

The project is licensed under Apache License v2.0 with LLVM Exceptions.
See LICENSE.TXT for details.