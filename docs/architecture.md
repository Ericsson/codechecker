
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

## Buildlogger / CMake
Generate a Compilation database (in json format) which can be processed by CodeChecker.
Buildlogger is built-in CodeChecker. Generating the compilation database can be automatically done.

## Buildaction job list
Based on the Compilation database a Buildaction is created for each analyzer.

## Analyzer client
Multiple analyzer clients can run parallel.  
Each Analyzer client:
  - processes one Buildaction
  - constructs the analysis command
  - runs an analyzer
  - postprocesses analysis results if required
  - sends the analysis results trough Thift binary protocol to the Report storage server

In quickcheck mode the results are only printed to the standard output. Nothing is stored into a database.

## Report Storage server
- Provides a Thrift API for result storage.
- Stores the analysis results to the database.
- Detects duplicate results (result in header file detected by multiple analyzer runs).
- Handles that source file contents are stored only once.
- Uses SQLAlchemy to connect to a database backend.

## Database
- Store multiple analyzer run results.
- Data can be used to generate analysis statistics.

## Report viewer server
- Multiple clients can connect simultaneously to the report viewer server.
- Uses SQLAlchemy to connect to a database backend.
- Provides a simple https webserver to view documentation.

## Command line client
- Simple client to view/compare results.
- Can be used for automated scripts for result processing.
- Provides plaintext and json output.

## Web browser client
- Client to view/filter/compare analysis results.
- Results are dynamically rendered based on the database content.
