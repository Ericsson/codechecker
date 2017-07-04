Issue report guidelines
=======================
Please insert every possible information you can obtain that could help us
reproduce and triage your issue. This usually includes:

 * The relevant parts from CodeChecker's output.
 * The version number of CodeChecker &ndash; execute
   `CodeChecker version --verbose debug` and copy the value for `Git tag info`.
 * What you were trying to do.
 * What behaviour was expected instead of what happened.


Contribution guidelines
=======================

Python style
------------
In CodeChecker, we use the [PEP-8](https://www.python.org/dev/peps/pep-0008)
rules in our coding style. _PEP-8_ is enforced by the test infrastructure
&ndash; if you write a new module outside the current directory structure,
make sure to add its path to [`tests/Makefile`](`tests/Makefile`) under the
`pep8` target.

In addition to the general rules of _PEP-8_, please keep the following rules
while writing your code:

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
  7. Modules from CodeChecker's own library's, `libcodechecker`.
  8. _(Empty line)_
  9. Imports from the package where the file you are writing is located in.

Between each of these _levels_, imports are sorted alphabetically on the
importing module's name, even if we only import a single class or function from
it.

#### Example
The example below should concisely show how module imports should be
structured:

~~~~{.py}
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

# -- 7. libcodechecker and subpackages, etc.
from libcodechecker import host_check
from libcodechecker import util
from libcodechecker.analyze import analyzer
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.database_handler import SQLServer
from libcodechecker.log import build_action
from libcodechecker.logger import LoggerFactory

# -- 9. imports from the local package
import client_db_access_handler

# ... your code here
~~~~

### Directory layout
`libcodechecker` is the folder where all CodeChecker related source code is
found. CodeChecker is organised into different entry-points based on different
features of the program, such as logging, analysing, result storage, web
server, etc. All these features have their own module under `libcodechecker`.

A CodeChecker feature having its entry point consists of a bare minimum of
two (2) things:

 * An entry point under `bin/codechecker-myfeature`.
 * The entry point's definition containing the feature's command-line help and
   argument parser under `libcodechecker/myfeature.py`.

Additionally, you may use different Python files to store code for your library
for better code organisation. Library code related to `myfeature` go into the
`libcodechecker/myfeature` folder.

If the library code is used between multiple subcommands, the file is put into
`libcodechecker` itself. Please try to localise your library code in its own
folder as much as possible.

Do **NOT** do _cross-subcommand_ import, aka. `from libcodechecker.analyze` in
a `libcodechecker.myfeature` file. This might change in the future as we
consider how to make CodeChecker a more modular application.

Please execute `scripts/create_new_subcommand.py myfeature` to automatically
generate the skeleton for `myfeature`. Already existing files, such as
`libcodechecker/log.py` give a nice overview on how entry-point handlers should
be laid out.
