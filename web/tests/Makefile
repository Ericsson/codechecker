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
PYTHON_BIN ?= python3

REPO_ROOT ?= REPO_ROOT=$(ROOT)
CC_TEST_WORKSPACE_ROOT ?= $(BUILD_DIR)/workspace
WOKSPACE_GLOBAL_AUTH_SERVER = $(CC_TEST_WORKSPACE_ROOT)/global_auth_server
WOKSPACE_GLOBAL_SIMPLE_SERVER = $(CC_TEST_WORKSPACE_ROOT)/global_simple_server

CLEAR_WORKSPACE_CMD = rm -rf $(CC_TEST_WORKSPACE_ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pycodestyle pylint test_unit test_functional

test_in_env: pycodestyle_in_env pylint_in_env test_unit_in_env test_functional_novenv

PYCODESTYLE_TEST_CMD = pycodestyle \
  --exclude=server/codechecker_server/migrations \
  codechecker_web tests \
  client/codechecker_client \
  server/codechecker_server server/tests \
  tests

pycodestyle:
	$(PYCODESTYLE_TEST_CMD)

pycodestyle_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYCODESTYLE_TEST_CMD)

PYLINT_TEST_CMD = PYLINTRC=$(ROOT)/.pylintrc \
  pylint -j0 \
    --ignore=server/codechecker_server/migrations/report,server/codechecker_server/migrations/report/versions,server/codechecker_server/migrations/config,server/codechecker_server/migrations/config/versions \
    ./bin/** \
    ./codechecker_web \
    ./client/bin/** ./client/codechecker_client \
    ./server/bin/** ./server/codechecker_server ./server/tests/unit \
    ./tests/functional ./tests/libtest ./tests/tools

pylint:
	$(PYLINT_TEST_CMD)

pylint_in_env:
	$(ACTIVATE_DEV_VENV) && $(PYLINT_TEST_CMD)

CODECHECKER_CMD = $(BUILD_DIR)/CodeChecker/bin/CodeChecker
SHUTDOWN_GLOBAL_SERVERS_CMD = \
  for TEST_ROOT in ${WOKSPACE_GLOBAL_AUTH_SERVER} ${WOKSPACE_GLOBAL_SIMPLE_SERVER}; do \
    if [ -d "$${TEST_ROOT}" ]; then \
      echo "Shutting down server..."; \
      HOME="$${TEST_ROOT}" ${CODECHECKER_CMD} server -l; \
      HOME="$${TEST_ROOT}" ${CODECHECKER_CMD} server \
        --config-directory $${TEST_ROOT} \
        --port `cat "$${TEST_ROOT}/serverport"` --stop; \
      rm -f "$${TEST_ROOT}/serverport"; \
      HOME="$${TEST_ROOT}" ${CODECHECKER_CMD} server -l; \
    fi \
  done

# Preserve the error status of the previous command but always be able to
# shut down servers.
EXIT_ERROR = { ${SHUTDOWN_GLOBAL_SERVERS_CMD}; exit 1; }

FUNCTIONAL_TEST_CMD = $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) $(CLANG_VERSION) $(TEST_PROJECT) \
  nosetests $(NOSECFG) tests/functional \
  && { ${SHUTDOWN_GLOBAL_SERVERS_CMD}; } || ${EXIT_ERROR}

MAKE_DB_CMD = bash -c 'psql -h localhost \
  -p $${TEST_DBPORT} -U $${TEST_DBUSERNAME} postgres \
  -c "CREATE DATABASE codechecker_config_$${CODECHECKER_DB_DRIVER}"'

DROP_DB_CMD = bash -c 'psql -h localhost \
  -p $${TEST_DBPORT} -U $${TEST_DBUSERNAME} postgres \
  -c "DROP DATABASE IF EXISTS codechecker_config_$${CODECHECKER_DB_DRIVER}"'

RUN_TEST_CMD = $(CLEAR_WORKSPACE_CMD) && \
  $(REPO_ROOT) BUILD_DIR=$(BUILD_DIR) $(CLANG_VERSION) $(TEST_PROJECT) \
  nosetests $(NOSECFG) $(ROOT)/web/${TEST} \
  && { ${SHUTDOWN_GLOBAL_SERVERS_CMD}; } || ${EXIT_ERROR}

run_test:
	$(RUN_TEST_CMD)

run_test_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(RUN_TEST_CMD)

test_unit: test_unit_server test_unit_client

test_unit_cov: test_unit_cov_server test_unit_cov_client

test_unit_in_env: test_unit_server_in_env test_unit_client_in_env

test_unit_cov_in_env: test_unit_cov_server_in_env test_unit_cov_client_in_env

test_functional: test_sqlite test_psql

test_functional_in_env: test_sqlite_in_env test_psql_in_env

test_sqlite:
	${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_sqlite_in_env: venv_dev
	${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1;
	$(ACTIVATE_DEV_VENV) && $(CLEAR_WORKSPACE_CMD) && $(FUNCTIONAL_TEST_CMD)

test_psql: test_psql_psycopg2 test_psql_pg8000

test_psql_in_env: test_psql_psycopg2_in_env test_psql_pg8000_in_env

PSYCOPG2_TEST_CMD = ${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1; \
  $(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD) && \
  $(DBUNAME) $(DBPORT) $(PSYCOPG2) $(MAKE_DB_CMD) && \
  $(CLEAR_WORKSPACE_CMD) && \
  $(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
  $(FUNCTIONAL_TEST_CMD) && \
  $(DBUNAME) $(DBPORT) $(PSYCOPG2) $(DROP_DB_CMD)

test_psql_psycopg2:
	$(PSYCOPG2_TEST_CMD)

test_psql_psycopg2_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PSYCOPG2_TEST_CMD)

PG8000_TEST_CMD = ${PYTHON_BIN} $(ROOT)/scripts/test/check_clang.py || exit 1; \
  $(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD) && \
  $(DBUNAME) $(DBPORT) $(PG8000) $(MAKE_DB_CMD) && \
  $(CLEAR_WORKSPACE_CMD) && \
  $(PSQL) $(DBUNAME) $(DBPORT) $(PG8000) \
  $(FUNCTIONAL_TEST_CMD) && \
  $(DBUNAME) $(DBPORT) $(PG8000) $(DROP_DB_CMD)

test_psql_pg8000:
	$(PG8000_TEST_CMD)

test_psql_pg8000_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PG8000_TEST_CMD)

test_clean:
	$(CLEAR_WORKSPACE_CMD)

# Use the proper requirement file for the given test configuration
test_matrix_sqlite: VENV_DEV_REQ_FILE = web/requirements_py/dev/requirements.txt
test_matrix_sqlite: test_unit test_sqlite

test_matrix_psql_psycopg2: VENV_DEV_REQ_FILE = web/requirements_py/db_psycopg2/requirements.txt
test_matrix_psql_psycopg2: test_unit test_psql_psycopg2

test_matrix_psql_pg8000: VENV_DEV_REQ_FILE = requirements_py/db_pg8000/requirements.txt
test_matrix_psql_pg8000: test_unit test_psql_pg8000
