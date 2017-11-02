# Architecture overview

~~~~
Architecture

                                                         .---------.
                                                         | Web     |
          .-------------.      .----------.              | browser |
          | Buildaction | ---> .----------.              | client  |
          | job list    | ---> .----------.------.       '---------'.---------.
          |             | ---> | Analyzer |------|            ^     | Command |
          '-------------'      | client   |------|            |---->| line    |
                ^              '----------'      |            |     | client  |
                |                                |            |     '---------'
                |                      Binary protocol    Json protocol
        .-----------------.                      |            |
        | Compilation     |                      v            v
        | database (json) |               .------------.------------.
        '-----------------'               | Thrift API | Thrift API |
                ^                         '------------'------------'
                |                         | Report     | Report     |
                |                         | storage    | viewer     |
         .---------------.                | server     | server     |
         | Buildlogger / |                '------------'------------'
         | CMake         |                      ^           ^
         '---------------'                      |           |
                                                SQLAlchemy ORM
                                                |           |
                                                v           v

                                               SQLite/PostgreSQL
                                                 _.-----._
                                               .-         -.
                                               |-_       _-|
                                               |  ~-----~  |
                                               |           |
                                               `._       _.'
                                                  "-----"
~~~~

Table of Contents
=================
* [Buildlogger / CMake](#buildlogger-cmake)
* [Buildaction job list](#buildaction-job-list)
* [Analyzer client](#analyzer-client)
* [Report Storage server](#report-storage-server)
* [Database](#database)
* [Report viewer server](#report-viewer-server)
* [Command line client](#command-line-client)
* [Web browser client](#web-browser-client)
  
## <a name="buildlogger-cmake"></a> Buildlogger / CMake
Generate a Compilation database (in json format) which can be processed by CodeChecker.
Buildlogger is built-in CodeChecker. Generating the compilation database can be automatically done.

## <a name="buildaction-job-list"></a> Buildaction job list
Based on the Compilation database a Buildaction is created for each analyzer.

## <a name="analyzer-client"></a> Analyzer client
Multiple analyzer clients can run parallel.  
Each Analyzer client:
  - processes one Buildaction
  - constructs the analysis command
  - runs an analyzer
  - postprocesses analysis results if required
  - sends the analysis results trough Thift binary protocol to the Report storage server

In quickcheck mode the results are only printed to the standard output. Nothing is stored into a database.

## <a name="report-storage-server"></a> Report Storage server
- Provides a Thrift API for result storage.
- Stores the analysis results to the database.
- Detects duplicate results (result in header file detected by multiple analyzer runs).
- Handles that source file contents are stored only once.
- Uses SQLAlchemy to connect to a database backend.

## <a name="database"></a> Database
- Store multiple analyzer run results.
- Data can be used to generate analysis statistics.

## <a name="report-viewer-server"></a> Report viewer server
- Multiple clients can connect simultaneously to the report viewer server.
- Uses SQLAlchemy to connect to a database backend.
- Provides a simple https webserver to view documentation.

## <a name="command-line-client"></a> Command line client
- Simple client to view/compare results.
- Can be used for automated scripts for result processing.
- Provides plaintext and json output.

## <a name="web-browser-client"></a> Web browser client
- Client to view/filter/compare analysis results.
- Results are dynamically rendered based on the database content.
