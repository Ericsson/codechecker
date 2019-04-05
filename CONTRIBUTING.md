# Issue report guidelines

Please insert every possible information you can obtain that could help us
reproduce and triage your issue. This usually includes:

 * The relevant parts from CodeChecker's output.
 * The version number of CodeChecker &ndash; execute
   `CodeChecker version --verbose debug` and copy the value for `Git tag info`.
 * What you were trying to do.
 * What behaviour was expected instead of what happened.


## Contribution guidelines

### Python style
In CodeChecker, we use [pycodestyle](https://pypi.python.org/pypi/pycodestyle/)
and [pylint](https://www.pylint.org/) to automatically check our coding style.
`pycodestyle` and `pylint` are enforced by the test infrastructure &ndash;
if you write a new module outside the current directory structure, make sure to
add its path to [`web/tests/Makefile`](`web/tests/Makefile`) or
[`analyzer/tests/Makefile`](analyzer/tests/Makefile) under the `pycodestyle`
and `pylint` targets.

In addition to the general rules of `pycodestyle`, please keep the following
rules while writing your code:

  * Comments must be whole sentences, beginning with a capital letter and
    ending with a closing `.`.

### Order of `import` commands
Order your `import` commands according to as follows:

  1. **System-wide** imports come first and foremost, e.g.
    `import multiprocessing`.
  2. _(Empty line for readability)_
  3. External module/library imports that are not system-wide but related to
     CodeChecker's **dependencies**, e.g. `from thrift import Thrift`.
  4. _(Empty line)_
  5. **API** imports, e.g. `import shared` and `from Authentication import
     ttypes`. The only special rule about this clause is that `import shared`
     comes before every _other_ API import.
  6. _(Empty line)_
  7. Modules from CodeChecker's own library's, `codechecker_common`,
  `codechecker_analyzer`, `codechecker_web`, `codechecker_client`,
  `codechecker_server` etc.
  8. _(Empty line)_
  9. Imports from the package where the file you are writing is located in.

Between each of these _levels_, imports are sorted alphabetically on the
importing module's name, even if we only import a single class or function from
it.

#### Example
The example below should concisely show how module imports should be
structured:

```py
# ...General LICENSE information and file header...
"""
Documentation about the module.
"""

# -- 1. System specific imports
import atexit
from multiprocessing import Pool
import os
import tempfile

# -- 3. CodeChecker dependency imports
from alembic import config  # sorted as 'a'
import sqlalchemy
from sqlalchemy.engine import Engine
from thrift import Thrift
from thrift.Thrift import TException
from thrift.protocol import TJSONProtocol

# -- 5. API imports
import shared
from Authentication import codeCheckerAuthentication
from Authentication import constants
from codeCheckerDBAccess import codeCheckerDBAccess
from codeCheckerDBAccess.ttypes import *

# -- 7. codechecker_analyzer, codechecker_common and subpackages, etc.
from codechecker_analyzer import analyzer
from codechecker_analyzer.analyzers import analyzer_types
from codechecker_analyzer.buildlog import build_action
from codechecker_common import host_check
from codechecker_common import util

# -- 9. imports from the local package
from . import client_db_access_handler
from product_db_access_handler import ThriftProductHandler

# ... your code here
```

### Directory layout
#### `analyzer`
This folder contains source code of the CodeChecker `analyzer` and
`build-logger`.

The `build-logger` can be found under the `tools` folder. This can be used to
capture the build process and generate a JSON compilation database.

#### `bin`
This folder contains entry points of the CodeChecker package such as
`codechecker-version` and wrapper scripts.

#### `codechecker_common`
`codechecker_common` is a python package where all common CodeChecker related
source code is found which are used by the analyzer and web part of
CodeChecker.

#### `config`
This folder contains common configuration files such as
`checker_severity_map.json`, `logger.conf` etc. which are used by the
`analyzer` and the `web` part of CodeChecker.

#### `docker`
This folder contains docker related files.

#### `docs`
This folder contains documentation files for the CodeChecker.

#### `scripts`
This folder contains multiple scripts which are used at the build process of
CodeChecker, gerrit integration, debug etc.

#### `tools`
This folder contains tools which are used by the `analyzer` and `web` part
of the CodeChecker such as `plist-to-html` and `tu_collector`.

#### `web`
This folder contains source code of the CodeChecker web server and web client.

### Entry points
CodeChecker is organized into different entry-points based on different
features of the program, such as logging, analysing, result storage, web
server, etc.

A CodeChecker feature having its entry point consists of a bare minimum of
two (2) things:

 * An entry point under `bin/codechecker-myfeature`.
 * The entry point's definition containing the feature's command-line help and
   argument parser under `cmd/myfeature.py`.

### Libraries
CodeChecker contains multiple python packages:
 * `codechecker_common`: used by the analyzer and web part of the CodeChecker.
 * `codechecker_analyzer`: contains source code of the CodeChecker analyzer.
 * `codechecker_web`: used by the WEB server and client.
 * `codechecker_client`: contains source code of the CodeChecker WEB client.
 * `codechecker_server`: contains source code of the CodeChecker WEB server.
 * `codechecker_api`: python api module files which are generated by a thrift
   compiler.

Additionally, you may use different Python files to store code for your library
for better code organisation. For example a server library code related to
`myfeature` go into the `codechecker_server/myfeature` folder. Please try to
localise your library code in its own folder as much as possible.

Do **NOT** do _cross-subcommand_ import, aka.
`from codechecker_analyzer.analyze` in a `codechecker_server.myfeature` file.
This might change in the future as we consider how to make CodeChecker a more
modular application.

Please execute `scripts/create_new_subcommand.py myfeature` to automatically
generate the skeleton for `myfeature`. Already existing files, such as
`codechecker_analyzer/cmd/log.py` give a nice overview on how entry-point
handlers should be laid out.
