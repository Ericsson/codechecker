# Environment variables to run tests.

CURRENT_DIR = ${CURDIR}
# Root of the repository.
REPO_ROOT ?= $(CURRENT_DIR)/..
REPO_ROOT_ENV_VAR ?= REPO_ROOT=$(REPO_ROOT)

MYPY_CMD = mypy --ignore-missing-imports $(REPO_ROOT)/codechecker_common

mypy:
	$(MYPY_CMD)

mypy_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(MYPY_CMD)

test: test_unit

test_in_env: test_unit_in_env

# pytest test runner configuration options.
PYTESTCFG = -c pytest.ini ${EXTRA_PYTEST_ARGS}
UNIT_TEST_CMD = $(REPO_ROOT_ENV_VAR) pytest $(PYTESTCFG) tests/unit

test_unit:
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)
