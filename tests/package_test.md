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
 * The chosen test project is builded, logged and checked twice. For this step the ld-logger must be present in the package.
 * The test modules are invoked.


# Test modules
The tests are based on python unittest so each test file should contain a class inheriting from _unittest.TestCase_.
The test cases are given the port of the viewer server and the project info by environment variables (CC_TEST_VIEWER_PORT, CC_TEST_PROJECT_INFO).

The _test_helper.thrift_client_to_db_ module contains _CCViewerHelper_ which is a wrapper for the thrift viewer api.


# Test projects
Test projects can be found in _tests/test_projects/_ .
Test projects must have _project_info.json_ in their root directory. This file contains the build commands and other data required by the test modules.
The build commands are executed in bash, in the project's root directory.
