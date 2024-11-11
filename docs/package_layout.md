# CodeChecker package builder

Short description for the package layout of the generic CodeChecker package.
Package creation is based on the package layout config file.
It has two main parts a static and a runtime part.

### External checker libraries
External checker libraries can be used in the package. The shared object files
should be in the plugin directory and will be automatically loaded at runtime.

## Runtime section
The runtime part contains information which will be used only at runtime
to find files during the checking process.

### Analyzers section
This section can be used to register multiple analyzers and their binaries:
```json
"analyzers": {
    "clangsa": "clang",
    "clang-tidy": "/path/to/clang-tidy"
}
```

The given binaries can be absolute or relative (to the package root directory)
paths.

You can set the `CC_ANALYZERS_FROM_PATH` environment variable before running a
CodeChecker command to `yes` or `1` to enforce taking the analyzers from the
`PATH` instead of the given binaries. If this option is set you can also
configure the plugin directory of the Clang Static Analyzer by using the
`CC_CLANGSA_PLUGIN_DIR` environment variable.

### Replacer section
This section is a key-value component. The key is `clang-apply-replacements`
and the value is the same by default. This is the name of a Clang tool which
applies textual replacements in the source code directly. `CodeChecker fixit`
command uses this tool, see its documentation for further details.
