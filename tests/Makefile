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

pep8:
	pep8 codechecker codechecker_lib db_model scripts storage_server viewer_server viewer_clients tests

run_test: venv_dev package
	. venv_dev/bin/activate && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) ${TEST}

test_unit: venv_dev
	. venv_dev/bin/activate && nosetests $(NOSECFG) tests/unit

test_functional: test_sqlite test_psql

test_sqlite: package venv_dev
	. venv_dev/bin/activate && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		nosetests $(NOSECFG) tests/functional

test_psql: test_psql_psycopg2 test_psql_pg8000

test_psql_psycopg2: package venv_dev
	. venv_dev/bin/activate && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) \
		nosetests $(NOSECFG) tests/functional

test_psql_pg8000: package venv_dev
	. venv_dev/bin/activate && \
		$(REPO_ROOT) $(CLANG_VERSION) $(TEST_PROJECT) \
		$(PSQL) $(DBUNAME) $(DBPORT) $(PG800) \
		nosetests $(NOSECFG) tests/functional

test_clean:
	rm -rf build/workspace
