# Environment variables to run tests.

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pycodestyle pylint test_unit test_functional

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env

PYCODESTYLE_TEST_CMD = pycodestyle warning_to_plist tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = PYLINTRC=$(ROOT)/.pylintrc \
	pylint ./warning_to_plist ./tests/**

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) \
  nosetests $(NOSECFG) tests/unit

test_unit:
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) \
  nosetests $(NOSECFG) tests/functional

test_functional:
	$(FUNCTIONAL_TEST_CMD)

test_functional_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)
