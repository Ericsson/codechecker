SERVER_UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) pytest $(PYTESTCFG) server server/tests/unit
SERVER_UNIT_TEST_COV_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) coverage run -m pytest $(PYTESTCFG) server server/tests/unit && coverage report && coverage html

test_unit_server:
	$(SERVER_UNIT_TEST_CMD)

test_unit_cov_server:
	$(SERVER_UNIT_TEST_COV_CMD)

test_unit_server_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(SERVER_UNIT_TEST_CMD)

test_unit_cov_server_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(SERVER_UNIT_TEST_COV_CMD)
