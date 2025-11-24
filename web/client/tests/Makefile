CLIENT_UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) pytest $(PYTESTCFG) client client/tests/unit
CLIENT_COVERAGE_CMD = $(REPO_ROOT) $(PYTHON_BIN) -m coverage
CLIENT_COVERAGE_RCFILE = --rcfile=$(ROOT)/.coveragerc
CLIENT_COVERAGE_SOURCE = codechecker_client,codechecker_web,codechecker_common
CLIENT_UNIT_TEST_COV_CMD = mkdir -p build/coverage && \
	$(CLIENT_COVERAGE_CMD) erase $(CLIENT_COVERAGE_RCFILE) && \
	$(CLIENT_COVERAGE_CMD) run $(CLIENT_COVERAGE_RCFILE) --source=$(CLIENT_COVERAGE_SOURCE) -m pytest $(PYTESTCFG) client client/tests/unit && \
	$(CLIENT_COVERAGE_CMD) report $(CLIENT_COVERAGE_RCFILE) && \
	$(CLIENT_COVERAGE_CMD) html $(CLIENT_COVERAGE_RCFILE)


test_unit_client:
	$(CLIENT_UNIT_TEST_CMD)

test_unit_cov_client:
	$(CLIENT_UNIT_TEST_COV_CMD)

test_unit_client_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(CLIENT_UNIT_TEST_CMD)

test_unit_cov_client_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(CLIENT_UNIT_TEST_COV_CMD)
