# Environment variables to run tests.

CURRENT_DIR = ${CURDIR}
# Root of the repository.
REPO_ROOT ?= REPO_ROOT=$(CURRENT_DIR)/../../../

# Nose test runner configuration options.
NOSECFG = --config .noserc

test_in_env: test_unit_in_env

test: test_unit

UNIT_TEST_CMD = $(REPO_ROOT) nosetests $(NOSECFG) .
UNIT_TEST_COV_CMD = $(REPO_ROOT) coverage run -m nose $(NOSECFG) . && coverage report && coverage html

test_unit:
	$(UNIT_TEST_CMD)

test_unit_cov:
	$(UNIT_TEST_COV_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_cov_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_COV_CMD)
