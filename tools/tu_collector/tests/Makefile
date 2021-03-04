# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: mypy pycodestyle pylint test_unit

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env

MYPY_TEST_CMD = mypy --ignore-missing-imports tu_collector tests

mypy:
	$(MYPY_TEST_CMD)

mypy_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(MYPY_TEST_CMD)

PYCODESTYLE_TEST_CMD = pycodestyle tu_collector tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = PYLINTRC=$(ROOT)/.pylintrc \
	pylint -j0 ./tu_collector ./tests/**

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
