UNIT_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) nosetests $(NOSECFG) -w server tests/unit

test_unit_server: venv_dev thrift
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_novenv_server: thrift
	$(UNIT_TEST_CMD)
