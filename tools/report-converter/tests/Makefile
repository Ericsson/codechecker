# Environment variables to run tests.

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

LAYOUT_DIR ?= LAYOUT_DIR=$(STATIC_DIR)

# pytest test runner configuration options.
PYTESTCFG = -c pytest.ini

test: mypy pycodestyle pylint test_unit test_functional

test_in_env: mypy_in_env pycodestyle_in_env pylint_in_env test_unit_in_env

MYPY_TEST_CMD = mypy --ignore-missing-imports codechecker_report_converter

mypy:
	$(MYPY_TEST_CMD)

mypy_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(MYPY_TEST_CMD)

PYCODESTYLE_TEST_CMD = pycodestyle codechecker_report_converter tests \
	--exclude tests/unit/analyzers/pyflakes_output_test_files/files

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = PYLINTRC=$(ROOT)/.pylintrc \
	pylint -j0 ./codechecker_report_converter ./tests/**

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) $(LAYOUT_DIR) \
  pytest $(PYTESTCFG) tests/unit

test_unit:
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) \
  pytest $(PYTESTCFG) tests/functional

test_functional:
	$(FUNCTIONAL_TEST_CMD)

test_functional_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)
