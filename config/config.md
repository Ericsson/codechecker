
# Package configuration

### Checker severity map
checker_severity_map.json file contains a mapping between a
checker name and a severity level. Severity levels can be found in the
codechecker_api_shared.thrift file.

The following severity levels are defined:

- **STYLE**: A true positive indicates that the source code is against a specific coding guideline or could improve readability.
Example: LLVM Coding Guideline: Do not use else or else if after something that interrupts control flow (break, return, throw, continue).

- **LOW**: A true positive indicates that the source code is hard to read/understand or could be easily optimized.
Example: Unused variables, Dead code.

- **MEDIUM**: A true positive indicates that the source code that may not cause a run-time error (yet), but against intuition and hence prone to error.
Example: Redundant expression in a condition. 

- **HIGH**: A true positive indicates that the source code will cause a run-time error.
  Example of this category: out of bounds array access, division by zero, memory leak.

- **CRITICAL**: Currently unused. This severity level is reserved for later use.

### Package configuration
  *  environment variables section  
     Contains enviroment variable names set and used during the static analysis
  *  package variables section  
     Default database username which will be used to initialize postgres database.  

  *  checker config section
     + checkers  
       This section contains the default checkers set used for analysis.
       The order of the checkers will be kept. (To enable set to true, to disable set to false)

### Session configuration
  * authentication section  
    Contains configuration for a **server** on how to handle authentication
  * credentials section  
    Contains the **client** user's preconfigured authentication tokens.
  * tokens section  
    Contains session tokens the **client** user has received through authentication. This section is **not** meant to be configured by hand.

### gdb script
Contains an automated gdb script which can be used for debug. In debug mode the failed build commands will be rerun with gdb.

### version
Version file contains version information for the package
