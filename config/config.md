
# Package configuration

### Checker severity map
checker_severity_map.json file contains a mapping between a
checker name and a severity level. Severity levels can be found in the shared.thrift file.

### Package configuration
  *  environment variables section  
     Contains enviroment variable names set and used during the static analysis
  *  package variables section
     Default database username which will be used to initialize postgres database.  

  *  checker config section
     + checkers
       This section contains the default checkers set used for analysis.
       The order of the checkers will be kept. (To enable set to true, to disable set to false)

### gdb script
Contains an automated gdb script which can be used for debug. In debug mode the failed build commands will be rerun with gdb.

### version
Version file contains version information for the package
