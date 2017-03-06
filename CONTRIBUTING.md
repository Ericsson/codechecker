Contribution guidelines
=======================

Python style
------------
In CodeChecker, we use the [PEP-8](https://www.python.org/dev/peps/pep-0008)
rules in our coding style. _PEP-8_ is enforced by the test infrastructure
&ndash; if you write a new module, make sure to add its path to
[`tests/Makefile`](`tests/Makefile`) under the `pep8` target.

In addition to the general ruleset of _PEP-8_, please keep the following rules
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
from libcodechecker import client

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

