## Code Analysis tools
CodeChecker can execute two main `C/C++` static analyzer tools:
- [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)
- [Clang Static Analyzer](https://clang-analyzer.llvm.org/)

We are planning to support more analyzer tools by creating a separate converter
tool which can be used to convert the output of different code analyzer tools
to a CodeChecker result directory which can be stored to a CodeChecker server.

| Language       | Analyzer     | Supported by CodeChecker |
| -------------- |--------------|---------------------|
| **C/C++**      | [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)  | ✓ |
|                | [Clang Static Analyzer](https://clang-analyzer.llvm.org/)    | ✓ |
|                | [Clang Sanitizers](#clang-sanitizers)    | ✓ |
|                | [Cppcheck](/tools/report-converter/README.md#cppcheck)    | ✓ |
|                | [Infer](https://fbinfer.com/)    | ✗ |
| **Java**       | [FindBugs](http://findbugs.sourceforge.net/)    | ✗ |
|                | [SpotBugs](https://spotbugs.github.io/)    | ✗ |
|                | [Infer](https://fbinfer.com/)    | ✗ |
| **Python**     | [Pylint](https://www.pylint.org/)    | ✗ |
|                | [Pyflakes](https://github.com/PyCQA/pyflakes)    | ✗ |
|                | [mypy](http://mypy-lang.org/)    | ✗ |
|                | [Bandit](https://github.com/PyCQA/bandit)    | ✗ |
| **JavaScript** | [ESLint](https://eslint.org/)    | ✗ |
|                | [JSHint](https://jshint.com/)    | ✗ |
|                | [JSLint](https://jslint.com/)    | ✗ |
| **Go**         | [Golint](https://github.com/golang/lint)    | ✗ |
|                | [Staticcheck](https://staticcheck.io/)    | ✗ |
|                | [go-critic](https://github.com/go-critic/go-critic)    | ✗ |

## Clang Sanitizers
| Name         | Supported by CodeChecker |
|--------------|---------------------|
| [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)    | ✓ |
| [ThreadSanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)    | ✓ |
| [MemorySanitizer](https://clang.llvm.org/docs/MemorySanitizer.html)    | ✓ |
| [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)    | ✓ |
| [DataFlowSanitizer](https://clang.llvm.org/docs/DataFlowSanitizer.html)    | ✗ |
| [LeakSanitizer](https://clang.llvm.org/docs/LeakSanitizer.html)    | ✗ |

We support to convert multiple sanitizer output to a CodeChecker report
directory which can be stored to a CodeChecker server by using our
[report-converter](/tools/report-converter) tool. For more information how to
use this tool see the [user guide](/tools/report-converter/README.md).
