# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)

LAYOUT_DIR ?= LAYOUT_DIR=$(STATIC_DIR)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: mypy pycodestyle pylint test_unit

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env

MYPY_TEST_CMD = mypy plist_to_html tests

mypy:
	$(MYPY_TEST_CMD)

mypy_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(MYPY_TEST_CMD)

PYCODESTYLE_TEST_CMD = pycodestyle plist_to_html tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = pylint -j0 ./plist_to_html ./tests \
  --disable=all \
  --enable=logging-format-interpolation,old-style-class,unused-wildcard-import,unused-import,unused-variable,len-as-condition,bad-indentation

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) $(LAYOUT_DIR) \
  nosetests $(NOSECFG) tests/unit

test_unit: dep
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev dep
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)
