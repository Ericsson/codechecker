# Environment variables to run tests.

CURRENT_DIR = $(shell pwd)
# Root of the repository.
REPO_ROOT ?= REPO_ROOT=$(CURRENT_DIR)/../../../

# Nose test runner configuration options.
NOSECFG = --config .noserc

test_in_env: test_unit_in_env

test: test_unit

UNIT_TEST_CMD = $(REPO_ROOT) nosetests $(NOSECFG) .

test_unit:
	$(UNIT_TEST_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)
