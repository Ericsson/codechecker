# Environment variables to run tests.

# Database settings can be overwritten by local
# Makefile
PSQL ?= TEST_USE_POSTGRESQL=true
PG800 ?= CODECHECKER_DB_DRIVER=pg8000
PSYCOPG2 ?= CODECHECKER_DB_DRIVER=psycopg2
DBPORT ?= TEST_DBPORT=5432
DBUNAME ?= TEST_DBUSERNAME=postgres

# Test project configuration, tests are run on these files.
CLANG_VERSION ?= TEST_CLANG_VERSION=stable
TEST_PROJECT ?= TEST_PROJ=$(CURRENT_DIR)/tests/projects/cpp

REPO_ROOT ?= REPO_ROOT=$(ROOT)

# Nose test runner configuration options.
NOSECFG = --config .noserc

test: pep8 test_unit test_functional

test_novenv: pep8 test_unit_novenv test_functional_novenv

pep8:
	pep8 bin libcodechecker scripts tests

UNIT_TEST_CMD = nosetests $(NOSECFG) tests/unit
FUNCTIONAL_TEST_CMD = $(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) tests/functional

run_test: package venv_dev
	$(ACTIVATE_DEV_VENV) && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST}

test_unit: venv_dev
	$(ACTIVATE_DEV_VENV) && $(UNIT_TEST_CMD)

test_unit_novenv:
	$(UNIT_TEST_CMD)

test_functional: test_sqlite test_psql
test_functional_novenv: test_sqlite_novenv test_psql_novenv

test_sqlite: package venv_dev
		$(ACTIVATE_DEV_VENV) && $(FUNCTIONAL_TEST_CMD)

test_sqlite_novenv: package
		$(FUNCTIONAL_TEST_CMD)

test_psql: test_psql_psycopg2 test_psql_pg8000
test_psql: test_psql_psycopg2_novenv test_psql_pg8000_novenv

test_psql_psycopg2: package venv_dev
	$(ACTIVATE_DEV_VENV) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD)

test_psql_psycopg2_novenv: package
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD)

test_psql_pg8000: package venv_dev
	$(ACTIVATE_DEV_VENV) && \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG800) \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD)

test_psql_pg8000_novenv: package
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG800) \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		$(FUNCTIONAL_TEST_CMD)

test_clean:
	rm -rf build/workspace

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*
