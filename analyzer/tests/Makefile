# Environment variables to run tests.

# Test project configuration, tests are run on these files.
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pylint pycodestyle test_unit test_functional test_build_logger test_tu_collector

test_novenv: test_unit_novenv test_functional_novenv

PYCODESTYLE_TEST_CMD = pycodestyle bin codechecker_analyzer tests

pycodestyle: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = pylint ./bin ./cmd ./codechecker_analyzer ./tests \
	--rcfile=$(ROOT)/.pylintrc \
  --disable=all \
  --enable=logging-format-interpolation,old-style-class

pylint: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

UNIT_TEST_CMD = $(REPO_ROOT) nosetests $(NOSECFG) tests/unit

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(TEST_PROJECT) \
		nosetests $(NOSECFG) tests/functional || exit 1

run_test: venv_dev
	$(ACTIVATE_DEV_VENV) && $(REPO_ROOT) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST} || exit 1

test_unit: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_novenv:
	$(UNIT_TEST_CMD)

test_functional: venv_dev
		python $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)

test_functional_novenv:
	python $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(FUNCTIONAL_TEST_CMD)

test_build_logger:
	make -C tools/build-logger -f Makefile.manual test

test_tu_collector:
	$(ACTIVATE_DEV_VENV) && \
	$(REPO_ROOT) make -C $(ROOT)/tools/tu_collector test
