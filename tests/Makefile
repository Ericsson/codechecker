# Environment variables to run tests.

# Database settings can be overwritten by local
# Makefile
PSQL ?= TEST_USE_POSTGRESQL=true
PG8000 ?= CODECHECKER_DB_DRIVER=pg8000
PSYCOPG2 ?= CODECHECKER_DB_DRIVER=psycopg2
DBPORT ?= TEST_DBPORT=5432
DBUNAME ?= TEST_DBUSERNAME=postgres

# Test project configuration, tests are run on these files.
CLANG_VERSION ?= TEST_CLANG_VERSION=stable
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects

REPO_ROOT ?= REPO_ROOT=$(ROOT)
WORKSPACE = $(BUILD_DIR)/workspace

CLEAR_WORKSPACE_CMD = rm -rf $(BUILD_DIR)/workspace

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pycodestyle pylint test_unit test_functional test_build_logger test_tu_collector

test_novenv: pycodestyle pylint test_unit_novenv test_functional_novenv

pycodestyle: venv_dev
	$(ACTIVATE_DEV_VENV) && \
	pycodestyle bin libcodechecker scripts tests vendor/plist_to_html vendor/tu_collector

pylint: venv_dev
	$(ACTIVATE_DEV_VENV) && \
	pylint bin libcodechecker scripts tests vendor/plist_to_html vendor/tu_collector --disable=all --enable=logging-format-interpolation

UNIT_TEST_CMD = $(REPO_ROOT) nosetests $(NOSECFG) tests/unit

CODECHECKER_CMD = $(BUILD_DIR)/CodeChecker/bin/CodeChecker
SHUTDOWN_SERVER_CMD = echo "Shutting down server..."; \
    HOME="$(WORKSPACE)" ${CODECHECKER_CMD} server -l; \
    HOME="$(WORKSPACE)" ${CODECHECKER_CMD} server \
			--config-directory $(WORKSPACE) \
	    --port `cat "$(WORKSPACE)/serverport"` --stop; \
    rm -f "$(WORKSPACE)/serverport"; \
    HOME="$(WORKSPACE)" ${CODECHECKER_CMD} server -l

# Preserve the error status of the previous command but always be able to
# shut down servers.
EXIT_ERROR = { ${SHUTDOWN_SERVER_CMD}; exit 1; }

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) tests/functional \
		&& { ${SHUTDOWN_SERVER_CMD}; } || ${EXIT_ERROR}

MAKE_DB_CMD = bash -c 'psql -h localhost \
		-p $${TEST_DBPORT} -U $${TEST_DBUSERNAME} postgres \
		-c "CREATE DATABASE codechecker_config_$${CODECHECKER_DB_DRIVER}"'

DROP_DB_CMD = bash -c 'psql -h localhost \
		-p $${TEST_DBPORT} -U $${TEST_DBUSERNAME} postgres \
		-c "DROP DATABASE IF EXISTS codechecker_config_$${CODECHECKER_DB_DRIVER}"'

run_test: venv_dev
	$(ACTIVATE_DEV_VENV) && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST} \
		&& { ${SHUTDOWN_SERVER_CMD}; } || ${EXIT_ERROR}

test_unit: venv_dev thrift
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_novenv: thrift
	$(UNIT_TEST_CMD)

test_functional: test_sqlite test_psql

test_functional_novenv: test_sqlite_novenv test_psql_novenv

test_sqlite: venv_dev
		python tests/check_clang.py || exit 1;
		$(ACTIVATE_DEV_VENV) && $(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_sqlite_novenv:
		python tests/check_clang.py || exit 1;
		$(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_psql: test_psql_psycopg2 test_psql_pg8000

test_psql_novenv: test_psql_psycopg2_novenv test_psql_pg8000_novenv

test_psql_psycopg2: venv_dev
	python tests/check_clang.py || exit 1;
	$(ACTIVATE_DEV_VENV) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD)

test_psql_psycopg2_novenv:
		python tests/check_clang.py || exit 1;
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(MAKE_DB_CMD) && \
				$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD)

test_psql_pg8000: venv_dev
	python tests/check_clang.py || exit 1;
	$(ACTIVATE_DEV_VENV) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG8000) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD)

test_psql_pg8000_novenv:
		python tests/check_clang.py || exit 1;
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG8000) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD)

test_clean:
	rm -rf build/workspace

# Use the proper requirement file for the given test configuration
test_matrix_sqlite: VENV_DEV_REQ_FILE = requirements_py/requirements.txt
test_matrix_sqlite: pycodestyle test_unit test_sqlite

test_matrix_psql_psycopg2: VENV_DEV_REQ_FILE = requirements_py/db_psycopg2/requirements.txt
test_matrix_psql_psycopg2: pycodestyle test_unit test_psql_psycopg2

test_matrix_psql_pg8000: VENV_DEV_REQ_FILE = requirements_py/db_pg8000/requirements.txt
test_matrix_psql_pg8000: pycodestyle test_unit test_psql_pg8000

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*

test_build_logger:
	cd vendor/build-logger; make -f Makefile.manual test

test_tu_collector:
	cd vendor/tu_collector; $(REPO_ROOT) make test
