## Code Analysis tools
CodeChecker can execute the following static analyzer tools:

- [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)
- [Clang Static Analyzer](https://clang-analyzer.llvm.org/)
- [Cppcheck](https://cppcheck.sourceforge.io/)
- [GCC Static Analyzer](https://gcc.gnu.org/wiki/StaticAnalyzer)
- [Facebook Infer Analyzer](https://fbinfer.com/)

We have created a separate [converter tool](tools/report-converter.md) which
can be used to convert the output of different source code analyzer tools to a
CodeChecker result directory which can be stored to a CodeChecker server.

| Language       | Analyzer     | Support storage of analyzer results |
| -------------- |--------------|---------------------|
| **C/C++**      | [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)  | ✓ |
|                | [Clang Static Analyzer](https://clang-analyzer.llvm.org/)    | ✓ |
|                | [Clang Sanitizers](#clang-sanitizers)    | ✓ |
|                | [Cppcheck](tools/report-converter.md#cppcheck)    | ✓ |
|                | [Facebook Infer](tools/report-converter.md#facebook-infer)    | ✓ |
|                | [Coccinelle](tools/report-converter.md#coccinelle)   | ✓ |
|                | [Smatch](tools/report-converter.md#smatch)   | ✓ |
|                | [Kernel-Doc](tools/report-converter.md#kernel-doc)   | ✓ |
|                | [Sparse](tools/report-converter.md#sparse)   | ✓ |
|                | [cpplint](tools/report-converter.md#cpplint)   | ✓ |
|                | [GNU GCC Static Analyzer](tools/report-converter.md#gcc)   | ✓ |
|                | [PVS-Studio](tools/report-converter.md#PVS-Studio) | ✓ |
| **C#**         | [Roslynator.DotNet.Cli](tools/report-converter.md#roslynatordotnetcli)  | ✓ |
|                | [PVS-Studio](tools/report-converter.md#PVS-Studio) | ✓ |
| **Java**       | [FindBugs](http://findbugs.sourceforge.net/)    | ✗ |
|                | [SpotBugs](tools/report-converter.md#spotbugs)    | ✓ |
|                | [Facebook Infer](tools/report-converter.md#facebook-infer)    | ✓ |
|                | [PVS-Studio](tools/report-converter.md#PVS-Studio) | ✓ |
| **Python**     | [Pylint](tools/report-converter.md#pylint)    | ✓ |
|                | [Pyflakes](tools/report-converter.md#pyflakes)    | ✓ |
|                | [mypy](http://mypy-lang.org/)    | ✗ |
|                | [Bandit](https://github.com/PyCQA/bandit)    | ✗ |
| **JavaScript** | [ESLint](https://eslint.org/)    | ✓ |
|                | [JSHint](https://jshint.com/)    | ✗ |
|                | [JSLint](https://jslint.com/)    | ✗ |
| **TypeScript** | [TSLint](tools/report-converter.md#tslint)    | ✓ |
| **Go**         | [Golint](tools/report-converter.md#golint)    | ✓ |
|                | [Staticcheck](https://staticcheck.io/)    | ✗ |
|                | [go-critic](https://github.com/go-critic/go-critic)    | ✗ |
| **Markdown**   | [Markdownlint](https://github.com/markdownlint/markdownlint)    | ✓ |
|                | [Sphinx](https://github.com/sphinx-doc/sphinx)    | ✓ |

## Clang Sanitizers
| Name         | Support storage of analyzer results |
|--------------|---------------------|
| [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)    | ✓ |
| [ThreadSanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)    | ✓ |
| [MemorySanitizer](https://clang.llvm.org/docs/MemorySanitizer.html)    | ✓ |
| [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)    | ✓ |
| [DataFlowSanitizer](https://clang.llvm.org/docs/DataFlowSanitizer.html)    | ✗ |
| [LeakSanitizer](https://clang.llvm.org/docs/LeakSanitizer.html)    | ✓ |

We support to convert multiple sanitizer output to a CodeChecker report
directory which can be stored to a CodeChecker server by using our
[report-converter](tools/report-converter.md) tool. For more information how to
use this tool see the [user guide](tools/report-converter.md).
