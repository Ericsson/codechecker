## Code Analysis tools
CodeChecker can execute two main `C/C++` static analyzer tools:

- [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)
- [Clang Static Analyzer](https://clang-analyzer.llvm.org/)

We have created a separate [converter tool](/tools/report-converter) which
can be used to convert the output of different source code analyzer tools to a
CodeChecker result directory which can be stored to a CodeChecker server.

| Language       | Analyzer     | Support storage of analyzer results |
| -------------- |--------------|---------------------|
| **C/C++**      | [Clang Tidy](https://clang.llvm.org/extra/clang-tidy/)  | ✓ |
|                | [Clang Static Analyzer](https://clang-analyzer.llvm.org/)    | ✓ |
|                | [Clang Sanitizers](#clang-sanitizers)    | ✓ |
|                | [Cppcheck](/docs/tools/report-converter.md#cppcheck)    | ✓ |
|                | [Facebook Infer](/docs/tools/report-converter.md#fbinfer)    | ✓ |
|                | [Coccinelle](/docs/tools/report-converter.md#coccinelle)   | ✓ |
|                | [Smatch](/docs/tools/report-converter.md#smatch)   | ✓ |
|                | [Kernel-Doc](/docs/tools/report-converter.md#kernel-doc)   | ✓ |
|                | [Sparse](/docs/tools/report-converter.md#sparse)   | ✓ |
|                | [cpplint](/docs/tools/report-converter.md#cpplint)   | ✓ |
| **Java**       | [FindBugs](http://findbugs.sourceforge.net/)    | ✗ |
|                | [SpotBugs](/docs/tools/report-converter.md#spotbugs)    | ✓ |
|                | [Facebook Infer](/docs/tools/report-converter.md#fbinfer)    | ✓ |
| **Python**     | [Pylint](/docs/tools/report-converter.md#pylint)    | ✓ |
|                | [Pyflakes](/docs/tools/report-converter.md#pyflakes)    | ✓ |
|                | [mypy](http://mypy-lang.org/)    | ✗ |
|                | [Bandit](https://github.com/PyCQA/bandit)    | ✗ |
| **JavaScript** | [ESLint](https://eslint.org/)    | ✓ |
|                | [JSHint](https://jshint.com/)    | ✗ |
|                | [JSLint](https://jslint.com/)    | ✗ |
| **TypeScript** | [TSLint](/docs/tools/report-converter.md#tslint)    | ✓ |
| **Go**         | [Golint](/docs/tools/report-converter.md#golint)    | ✓ |
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
[report-converter](/tools/report-converter) tool. For more information how to
use this tool see the [user guide](/docs/tools/report-converter.md).
