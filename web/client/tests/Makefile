CLIENT_UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) nosetests $(NOSECFG) -w client tests/unit
CLIENT_UNIT_TEST_COV_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) coverage run -m nose $(NOSECFG) -w client tests/unit && coverage report && coverage html


test_unit_client:
	$(CLIENT_UNIT_TEST_CMD)

test_unit_cov_client:
	$(CLIENT_UNIT_TEST_COV_CMD)

test_unit_client_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(CLIENT_UNIT_TEST_CMD)

test_unit_cov_client_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(CLIENT_UNIT_TEST_COV_CMD)
