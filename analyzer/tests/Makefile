# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects
PYTHON_BIN ?= python3

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env test_functional_in_env test_build_logger test_tu_collector_in_env

test: pycodestyle pylint test_unit test_functional test_build_logger test_tu_collector

PYCODESTYLE_TEST_CMD = pycodestyle codechecker_analyzer tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = $(MAKE) -C $(CURRENT_DIR)/tools/merge_clang_extdef_mappings pylint && \
	$(MAKE) -C $(CURRENT_DIR)/tools/statistics_collector pylint && \
	PYLINTRC=$(ROOT)/.pylintrc pylint -j0 ./bin/** ./codechecker_analyzer ./tests/**

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

run_test:
	$(REPO_ROOT) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST} || exit 1

run_test_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(REPO_ROOT) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST} || exit 1

UNIT_TEST_CMD = $(REPO_ROOT) nosetests $(NOSECFG) tests/unit
UNIT_TEST_COV_CMD = $(REPO_ROOT) coverage run -m nose $(NOSECFG) tests/unit && coverage report && coverage html

test_unit:
	$(UNIT_TEST_CMD)

test_unit_cov:
	$(UNIT_TEST_COV_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_cov_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_COV_CMD)

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) \
		nosetests $(NOSECFG) tests/functional || exit 1

test_functional:
	${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(FUNCTIONAL_TEST_CMD)

test_functional_in_env: venv_dev
		${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)

test_build_logger:
	make -C tools/build-logger -f Makefile.manual test

test_tu_collector:
	REPO_ROOT=$(REPO_ROOT) make -C $(ROOT)/tools/tu_collector test

test_tu_collector_in_env:
	$(ACTIVATE_DEV_VENV) && \
	REPO_ROOT=$(REPO_ROOT) make -C $(ROOT)/tools/tu_collector test

test_merge_clang_extdef_mappings:
	make -C tools/merge_clang_extdef_mappings test

test_merge_clang_extdef_mappings_in_env:
	$(ACTIVATE_DEV_VENV) && \
	make -C tools/merge_clang_extdef_mappings test

test_statistics_collector:
	make -C tools/statistics_collector test

test_statistics_collector_in_env:
	$(ACTIVATE_DEV_VENV) && \
	make -C tools/statistics_collector test
