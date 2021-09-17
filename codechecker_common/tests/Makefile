# Environment variables to run tests.

CURRENT_DIR = ${CURDIR}
# Root of the repository.
REPO_ROOT ?= $(CURRENT_DIR)/../..

# Nose test runner configuration options.
NOSECFG = --config .noserc

MYPY_CMD = mypy --ignore-missing-imports $(REPO_ROOT)/codechecker_common

mypy:
	$(MYPY_CMD)

mypy_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(MYPY_CMD)
