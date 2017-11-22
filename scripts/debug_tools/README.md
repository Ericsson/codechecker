Debug Tools
===========

These scripts may be used to aid debugging of clang crashes during analysis.
The goal is to reproduce the crash locally, i.e. using the source files in the
failure zip. During the process we take the original compile command database,
compiler includes and compiler target files and we create the modified version
of them (with `_DEBUG` postfix).  These modified files contain the paths
prefixed with the root of the source directory which holds the dependent source
files (`sources-root`).

`prepare_analyzer_cmd.py` creates a new clang static analyzer command
(`analyzer-command_DEBUG`) which may be executed immediately if cross
translation unit (CTU) was disabled.  However, to debug CTU analysis related
crashed in clang we have to synthetise the AST dump files too, so other phases
are needed which are done in `prepare_all_cmd_for_ctu.py`.  It executes
`CodeChecker` with ctu-collect, therefore `CodeChecker` must be in the `PATH`
and the proper venv must be set.

Example session for debugging a clang crash:
```sh
$ export WS=/your_own_path
$ cd reports/failed
$ unzip main.c_4c7feffae4c2b887abcdc37a3c88b2e5.plist.zip
$ $WS/CodeChecker/debug_tools/prepare_analyzer_cmd.py --clang $WS/llvm/build/debug/bin/clang --clang_plugin_name libericsson --clang_plugin_path $WS/codechecker_core_ws/build/debug/libericsson-checkers.so
$ bash analyzer-command_DEBUG
```

Example session for debuggin a CTU clang crash:
```sh
$ export WS=/your_own_path
$ export PATH=$WS/CodeChecker/build/CodeChecker/bin:$PATH
$ source $WS/CodeChecker/venv_dev/bin/activate
$ cd reports/failed
$ unzip main.c_4c7feffae4c2b887abcdc37a3c88b2e5.plist.zip
$ $WS/CodeChecker/debug_tools/prepare_all_cmd_for_ctu.py --clang $WS/llvm/build/debug/bin/clang --clang_plugin_name libericsson --clang_plugin_path $WS/codechecker_core_ws/build/debug/libericsson-checkers.so
$ bash analyzer-command_DEBUG
```
