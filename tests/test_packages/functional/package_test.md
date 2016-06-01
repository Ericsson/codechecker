# How to run the tests
~~~~~~{.sh}
test_package.py -p /path/to/the/package/ --clang {stable, trunk}
~~~~~~
In this case 'stable' means the latest stable clang release.
Specifying the correct clang version is essential since different versions of clang SA may produce different reports.

For other options see:
~~~~~~{.sh}
test_package.py --help
~~~~~~


# What happens during the test
 * The chosen test project is built, logged and checked twice. For this step the ld-logger must be present in the package.
 * The test modules are invoked.

# Test projects
Test projects can be found in `tests/test_projects/` .
Test projects must have `project_info.json` in their root directory. This file contains the build commands and other data required by the test modules.
The build commands are executed in bash, in the project's root directory.

# Test modules
The tests are based on python unittest so each test file should contain a class inheriting from `unittest.TestCase`.  
Available environment variables for the tests:

| Name | Description |
|---------------------------|------------------|
| CC_TEST_VIEWER_PORT       | Viewer server port, test clients should use this to use the thrift api|
| CC_TEST_PROJECT_INFO      | information about the C/C++ project used for testing number/type of bugs, filter results based on the `project_info.json` |

The test cases can use the port of the viewer server and the project info through environment variables:

The `test_utils.thrift_client_to_db` module contains `CCViewerHelper` which is a wrapper for the thrift viewer api.

# Nosetest config
Nosetest config file can be used to provide more information during the tests.  
Create a `.noserc` file in your home directory and add this configuration:
~~~~~~
[nosetests]
verbosity=3
stop=1
nocapture=1
~~~~~~

Further configuration options can be found here [Nosetest usage](http://nose.readthedocs.io/en/latest/usage.html).
