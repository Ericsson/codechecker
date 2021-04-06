# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pycodestyle pylint test_unit

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env

PYCODESTYLE_TEST_CMD = pycodestyle bazel_compile_commands tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = pylint -j0 ./bazel_compile_commands ./tests \
  --disable=all \
  --enable=logging-format-interpolation,old-style-class,unused-wildcard-import,unused-import,unused-variable,len-as-condition,bad-indentation

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) \
  nosetests $(NOSECFG) tests/unit

test_unit:
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)
