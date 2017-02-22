
### Packaging requirements
  *  [Git](https://git-scm.com/) (> 1.9.1)
  *  [Thrift compiler](https://thrift.apache.org/) (> 0.9.2) required to generate python and javascript files
  *  [Doxygen](http://www.stack.nl/~dimitri/doxygen/) (> 1.8) to generate documentation
  *  Build logging
    - It is possible to build package without the ld-logger. In that case no automatic compilation database generation is done. To build ld-logger 32 and 64 bit versions automatically, `gcc multilib` and `make` is required.
    - Compilation command database can be generated with CMake during the build (run `cmake` with the `CMAKE_EXPORT_COMPILE_COMMANDS` option). CodeChecker can process the generated compilation database at runtime.

  * Other external dependencies are automatically downloaded and
    copied to the necessary directories in the package.

### Runtime requirements
#### Basic
Javascript dependencies are automatically downloaded based on the ext_source_deps_config.json file during package build.
  *  [Clang Static analyzer](http://clang-analyzer.llvm.org/) (latest stable or [trunk](http://clang.llvm.org/get_started.html))
  *  [Clang Tidy](http://clang.llvm.org/extra/clang-tidy/) (available in the clang tools extra repository [trunk](http://clang.llvm.org/get_started.html))
  *  [Python2](https://www.python.org/) (> 2.7)
  *  [Alembic](https://pypi.python.org/pypi/alembic) (>= 0.8.2) database migration support is available only for PostgreSQL database
  *  [SQLAlchemy](http://www.sqlalchemy.org/) (>= 1.0.9) Python SQL toolkit and Object Relational Mapper, for supporting multiple database backends
     - [PyPi SQLAlchemy](https://pypi.python.org/pypi/SQLAlchemy) (> 1.0.2)
  * Thrift python modules. Cross-language service building framework to handle data transfer for report storage and result viewer clients
     -  [PyPi thrift](https://pypi.python.org/pypi/thrift/0.9.2)(> 0.9.2 )
  * [Codemirror](https://codemirror.net/) (MIT) - view source code in the browser
  * [Jsplumb](https://jsplumbtoolkit.com/) (community edition, MIT) - draw bug paths
  * [Marked](https://github.com/chjj/marked) (BSD) - view documentation for checkers written in markdown (generated dynamically)
  * [Dojotoolkit](https://dojotoolkit.org/) (BSD) - main framework for the web UI
  * [Highlightjs](https://highlightjs.org/) (BSD) - required for highlighting the source code

#### PostgreSQL
For the additional PostgreSQL dependencies see the [PostgreSQL setup](postgresql_setup.md) documentation.

\include ext_source_deps_config.json
