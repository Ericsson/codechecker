CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build

# environment variables to run tests
# database settings
PSQL = TEST_USE_POSTGRESQL=true
PG800 = CODECHECKER_DB_DRIVER=pg8000
PSYCOPG2 = CODECHECKER_DB_DRIVER=psycopg2
DBPORT = TEST_DBPORT=5432
DBUNAME = TEST_DBUSERNAME=postgres

# test project configuration, tests are run on these files
CLANG_VERSION = TEST_CLANG_VERSION=stable
TEST_PROJECT = TEST_PROJ=$(CURRENT_DIR)/tests/test_projects/test_files

# the build package which should be tested
PKG_TO_TEST = CC_PACKAGE=$(CURRENT_DIR)/build/CodeChecker

# test runner needs to know the root of the repository
ROOT = REPO_ROOT=$(CURRENT_DIR)

pep8:
	pep8 codechecker codechecker_lib tests db_model viewer_server viewer_clients

gen-docs:
	doxygen ./Doxyfile.in

thrift: build_dir

	if [ ! -d "$(BUILD_DIR)/gen-py" ]; then rm -rf build/gen-py; fi
	if [ ! -d "$(BUILD_DIR)/gen-js" ]; then rm -rf build/gen-js; fi

	thrift -r -o build -I thrift_api/ --gen py thrift_api/report_storage_server.thrift
	thrift -r -o build -I thrift_api/ --gen py --gen js:query thrift_api/report_viewer_server.thrift
	thrift -r -o build -I thrift_api/ --gen py thrift_api/authentication.thrift

package: build_dir gen-docs thrift
	if [ ! -d "$(BUILD_DIR)/CodeChecker" ]; then \
		$(ROOT) ./scripts/build_package.py -o $(CURRENT_DIR)/build; \
	fi

travis:
	# travis specific changes
	scripts/change_clang_version.py $(CURRENT_DIR)

build_dir:
	mkdir -p build

test: pep8 test_unit test_functional

test_unit:
	nosetests tests/unit

test_functional: test_sqlite test_psql

test_sqlite: package
	$(ROOT) $(CLANG_VERSION) $(TEST_PROJECT) $(PKG_TO_TEST) nosetests tests/functional

test_env_cfg: package
	# required variables should be already set in the environment
	$(ROOT) $(PKG_TO_TEST) nosetests tests/functional

test_psql: test_psql_psycopg2 test_psql_pg8000

test_psql_psycopg2: package
	$(ROOT) $(CLANG_VERSION) $(TEST_PROJECT) $(PKG_TO_TEST) $(PSQL) $(DBUNAME) $(DBPORT) $(PSYCOPG2) nosetests tests/functional

test_psql_pg8000: package
	$(ROOT) $(CLANG_VERSION) $(TEST_PROJECT) $(PKG_TO_TEST) $(PSQL) $(DBUNAME) $(DBPORT) $(PG800) nosetests tests/functional

venv:
	# virtual environment to run the package
	virtualenv -p /usr/bin/python2.7 venv && . venv/bin/activate && pip install -r .ci/basic_python_requirements

venv_dev:
	# virtual environment for development
	virtualenv -p /usr/bin/python2.7 venv && . venv/bin/activate && pip install -r .ci/python_requirements && pip install nose

clean_venv:
	rm -rf venv

clean:
	rm -rf build
	rm -rf gen-docs

