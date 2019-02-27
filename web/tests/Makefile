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

test: pycodestyle pylint test_unit test_functional

test_novenv: pycodestyle pylint test_unit_novenv test_functional_novenv

PYCODESTYLE_TEST_CMD = pycodestyle \
  --exclude=server/codechecker_server/migrations \
  bin cmd codechecker_web tests \
  client/bin client/codechecker_client client/cmd \
  server/bin server/codechecker_server server/cmd server/tests \
  tests

pycodestyle: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = pylint bin/codechecker-web-version cmd/web_version.py \
  codechecker_web \
  client/cmd/cmd.py client/cmd/store.py client/codechecker_client \
  server/bin/codechecker-server server/cmd/server.py \
  server/codechecker_server server/tests/unit \
	--rcfile=$(ROOT)/.pylintrc \
  --disable=all \
  --enable=logging-format-interpolation,old-style-class

pylint: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

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
		nosetests $(NOSECFG) $(ROOT)/web/${TEST} \
		&& { ${SHUTDOWN_SERVER_CMD}; } || ${EXIT_ERROR}

test_unit: test_unit_server

test_unit_novenv: test_unit_novenv_server

test_functional: test_sqlite test_psql

test_functional_novenv: test_sqlite_novenv test_psql_novenv

test_sqlite: venv_dev
		python $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(ACTIVATE_DEV_VENV) && $(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_sqlite_novenv:
		python $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_psql: test_psql_psycopg2 test_psql_pg8000

test_psql_novenv: test_psql_psycopg2_novenv test_psql_pg8000_novenv

test_psql_psycopg2: venv_dev
	python $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(ACTIVATE_DEV_VENV) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD)

test_psql_psycopg2_novenv:
		python $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(MAKE_DB_CMD) && \
				$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD)

test_psql_pg8000: venv_dev
	python $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(ACTIVATE_DEV_VENV) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG8000) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD)

test_psql_pg8000_novenv:
		python $(ROOT)/scripts/test/check_clang.py || exit 1;
		$(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(MAKE_DB_CMD) && \
		$(CLEAR_WORKSPACE_CMD) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG8000) \
		$(FUNCTIONAL_TEST_CMD) && \
		$(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD)

test_clean:
	rm -rf build/workspace

# Use the proper requirement file for the given test configuration
test_matrix_sqlite: VENV_DEV_REQ_FILE = requirements_py/dev/requirements.txt
test_matrix_sqlite: pycodestyle test_unit test_sqlite

test_matrix_psql_psycopg2: VENV_DEV_REQ_FILE = requirements_py/db_psycopg2/requirements.txt
test_matrix_psql_psycopg2: pycodestyle test_unit test_psql_psycopg2

test_matrix_psql_pg8000: VENV_DEV_REQ_FILE = requirements_py/db_pg8000/requirements.txt
test_matrix_psql_pg8000: pycodestyle test_unit test_psql_pg8000

