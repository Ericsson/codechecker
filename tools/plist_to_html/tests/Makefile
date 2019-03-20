# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)

LAYOUT_DIR ?= LAYOUT_DIR=$(STATIC_DIR)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: test_unit

test_novenv: test_unit_novenv

PYCODESTYLE_TEST_CMD = pycodestyle plist_to_html tests

pycodestyle: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = pylint ./plist_to_html ./tests \
  --disable=all \
  --enable=logging-format-interpolation,old-style-class

pylint: venv
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) $(LAYOUT_DIR) \
  nosetests $(NOSECFG) tests/unit

test_unit: venv_dev dep
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_novenv: dep
	$(UNIT_TEST_CMD)
