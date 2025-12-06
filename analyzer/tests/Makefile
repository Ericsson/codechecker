# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects
PYTHON_BIN ?= python3

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# pytest test runner configuration options.
PYTESTCFG = -c pytest.ini ${EXTRA_PYTEST_ARGS}

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env test_functional_in_env test_build_logger test_tu_collector_in_env

test: pycodestyle pylint test_unit test_functional test_build_logger test_tu_collector

PYCODESTYLE_TEST_CMD = pycodestyle codechecker_analyzer tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = $(MAKE) -C $(CURRENT_DIR)/tools/merge_clang_extdef_mappings pylint && \
	$(MAKE) -C $(CURRENT_DIR)/tools/statistics_collector pylint && \
	PYLINTRC=$(ROOT)/.pylintrc pylint -j0 ./codechecker_analyzer ./tests/**

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

is_TEST_set:
	@if [ -z ${TEST} ]; then \
		echo "!!!!!!!!!!!!!!! ERROR !!!!!!!!!!!!!!!"; \
		echo "Environmental variable 'TEST' is not set!"; \
		echo "'TEST' should be set to a test file/directory."; \
		echo "Example: 'TEST=tests/functional/suppress make test_analyzer_feature'."; \
		echo "Note: You may provide additional pytest argument by setting "\
		     "'EXTRA_PYTEST_ARGS', which allows you to select a specific test "\
				 "inside a test file (via the -k option)."; \
		echo "Example: EXTRA_PYTEST_ARGS='-k test_source_suppress_export'  TEST=tests/functional/suppress make test_analyzer_feature"; \
		echo "!!!!!!!!!!!!!!! ERROR !!!!!!!!!!!!!!!"; \
		exit 1; \
	fi

run_test: is_TEST_set
	$(REPO_ROOT) $(TEST_PROJECT) \
		pytest $(PYTESTCFG) ${TEST} || exit 1

run_test_in_env: venv_dev is_TEST_set
	$(ACTIVATE_DEV_VENV) && $(REPO_ROOT) $(TEST_PROJECT) \
		pytest $(PYTESTCFG) ${TEST} || exit 1

UNIT_TEST_CMD = $(REPO_ROOT) pytest $(PYTESTCFG) tests/unit
COVERAGE_CMD = $(REPO_ROOT) $(PYTHON_BIN) -m coverage
COVERAGE_RCFILE = --rcfile=$(ROOT)/.coveragerc
ANALYZER_COVERAGE_SOURCE = codechecker_analyzer,codechecker_common
UNIT_TEST_COV_CMD = mkdir -p build/coverage && \
	$(COVERAGE_CMD) erase $(COVERAGE_RCFILE) && \
	$(COVERAGE_CMD) run $(COVERAGE_RCFILE) --source=$(ANALYZER_COVERAGE_SOURCE) -m pytest $(PYTESTCFG) tests/unit && \
	$(COVERAGE_CMD) report $(COVERAGE_RCFILE) && \
	$(COVERAGE_CMD) html $(COVERAGE_RCFILE)

test_unit:
	$(UNIT_TEST_CMD)

test_unit_cov:
	$(UNIT_TEST_COV_CMD)

test_unit_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_cov_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_COV_CMD)

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) \
		pytest $(PYTESTCFG) tests/functional || exit 1

test_functional:
	${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(FUNCTIONAL_TEST_CMD)

test_functional_in_env: venv_dev
		${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)

test_build_logger:
	$(MAKE) -C tools/build-logger test

test_tu_collector:
	REPO_ROOT=$(REPO_ROOT) $(MAKE) -C $(ROOT)/tools/tu_collector test

test_tu_collector_in_env:
	$(ACTIVATE_DEV_VENV) && \
	REPO_ROOT=$(REPO_ROOT) $(MAKE) -C $(ROOT)/tools/tu_collector test

test_merge_clang_extdef_mappings:
	$(MAKE) -C tools/merge_clang_extdef_mappings test

test_merge_clang_extdef_mappings_in_env:
	$(ACTIVATE_DEV_VENV) && \
	$(MAKE) -C tools/merge_clang_extdef_mappings test

test_statistics_collector:
	$(MAKE) -C tools/statistics_collector test

test_statistics_collector_in_env:
	$(ACTIVATE_DEV_VENV) && \
	$(MAKE) -C tools/statistics_collector test
