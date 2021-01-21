SERVER_UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) nosetests $(NOSECFG) -w server tests/unit

test_unit_server:
	$(SERVER_UNIT_TEST_CMD)

test_unit_server_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(SERVER_UNIT_TEST_CMD)
