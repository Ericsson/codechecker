SERVER_UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) pytest $(PYTESTCFG) server server/tests/unit
SERVER_COVERAGE_CMD = $(REPO_ROOT) $(PYTHON_BIN) -m coverage
SERVER_COVERAGE_RCFILE = --rcfile=$(ROOT)/.coveragerc
SERVER_COVERAGE_SOURCE = codechecker_server,codechecker_web,codechecker_common
SERVER_UNIT_TEST_COV_CMD = mkdir -p build/coverage && \
	$(SERVER_COVERAGE_CMD) erase $(SERVER_COVERAGE_RCFILE) && \
	$(SERVER_COVERAGE_CMD) run $(SERVER_COVERAGE_RCFILE) --source=$(SERVER_COVERAGE_SOURCE) -m pytest $(PYTESTCFG) server server/tests/unit && \
	$(SERVER_COVERAGE_CMD) report $(SERVER_COVERAGE_RCFILE) && \
	$(SERVER_COVERAGE_CMD) html $(SERVER_COVERAGE_RCFILE)

test_unit_server:
	$(SERVER_UNIT_TEST_CMD)

test_unit_cov_server:
	$(SERVER_UNIT_TEST_COV_CMD)

test_unit_server_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(SERVER_UNIT_TEST_CMD)

test_unit_cov_server_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(SERVER_UNIT_TEST_COV_CMD)
