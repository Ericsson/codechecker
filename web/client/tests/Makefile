UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) nosetests $(NOSECFG) -w client tests/unit

test_unit_client:
	$(UNIT_TEST_CMD)

test_unit_client_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)
