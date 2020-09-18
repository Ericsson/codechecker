-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build
VENDOR_DIR = $(CURRENT_DIR)/vendor

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_BIN_DIR = $(CC_BUILD_DIR)/bin
CC_BUILD_WEB_DIR = $(CC_BUILD_DIR)/www
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python3

CC_WEB = $(CURRENT_DIR)/web
CC_SERVER = $(CC_WEB)/server/
CC_CLIENT = $(CC_WEB)/client/
CC_ANALYZER = $(CURRENT_DIR)/analyzer
CC_COMMON = $(CURRENT_DIR)/codechecker_common

CC_TOOLS = $(CURRENT_DIR)/tools
CC_ANALYZER_TOOLS = $(CC_ANALYZER)/tools

# Root of the repository.
ROOT = $(CURRENT_DIR)

# Set it to YES if you would like to build and package 64 bit only shared
# objects and ldlogger binary.
BUILD_LOGGER_64_BIT_ONLY ?= NO

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

default: package

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	mkdir -p $(CC_BUILD_LIB_DIR)

mkdocs_build:
	mkdocs build

build_plist_to_html:
	$(MAKE) -C $(ROOT)/tools/plist_to_html build

package_plist_to_html: build_plist_to_html package_dir_structure
	# Copy plist-to-html files.
	cp -r $(CC_TOOLS)/plist_to_html/build/plist_to_html/plist_to_html $(CC_BUILD_LIB_DIR)

build_tu_collector:
	$(MAKE) -C $(ROOT)/tools/tu_collector build

package_tu_collector: build_tu_collector package_dir_structure
	# Copy tu_collector files.
	cp -rp $(CC_TOOLS)/tu_collector/build/tu_collector/tu_collector $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/tu_collector/tu_collector.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/tu_collector/tu_collector.py bin/tu_collector

build_report_converter:
	$(MAKE) -C $(ROOT)/tools/report-converter build

package_report_converter: build_report_converter package_dir_structure
	# Copy tu_collector files.
	cp -rp $(CC_TOOLS)/report-converter/build/report_converter/codechecker_report_converter $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_report_converter/cli.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/codechecker_report_converter/cli.py bin/report-converter

build_report_hash:
	$(MAKE) -C $(ROOT)/tools/codechecker_report_hash build

package_report_hash: build_report_hash package_dir_structure
	cp -r $(CC_TOOLS)/codechecker_report_hash/build/codechecker_report_hash/codechecker_report_hash $(CC_BUILD_LIB_DIR)

build_merge_clang_extdef_mappings:
	$(MAKE) -C $(CC_ANALYZER)/tools/merge_clang_extdef_mappings build

package_merge_clang_extdef_mappings: build_merge_clang_extdef_mappings package_dir_structure
	# Copy merge-clang-extdef-mappings files.
	cp -r $(CC_ANALYZER)/tools/merge_clang_extdef_mappings/build/merge_clang_extdef_mappings/codechecker_merge_clang_extdef_mappings $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_merge_clang_extdef_mappings/cli.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/codechecker_merge_clang_extdef_mappings/cli.py bin/merge-clang-extdef-mappings

build_statistics_collector:
	$(MAKE) -C $(CC_ANALYZER_TOOLS)/statistics_collector build

package_statistics_collector: build_statistics_collector package_dir_structure
	# Copy statistics-collector files.
	cp -r $(CC_ANALYZER_TOOLS)/statistics_collector/build/statistics_collector/codechecker_statistics_collector $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_statistics_collector/cli.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/codechecker_statistics_collector/cli.py bin/post-process-stats

package_gerrit_skiplist:
	cp -p scripts/gerrit_changed_files_to_skipfile.py $(CC_BUILD_DIR)/bin

package: package_dir_structure set_git_commit_template package_plist_to_html package_tu_collector package_report_converter package_report_hash package_merge_clang_extdef_mappings package_statistics_collector package_gerrit_skiplist
	BUILD_DIR=$(BUILD_DIR) BUILD_LOGGER_64_BIT_ONLY=$(BUILD_LOGGER_64_BIT_ONLY) $(MAKE) -C $(CC_ANALYZER) package_analyzer
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) package_web

	# Copy libraries.
	mkdir -p $(CC_BUILD_LIB_DIR)/codechecker && \
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_ANALYZER)/codechecker_analyzer $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_WEB)/codechecker_web $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_SERVER)/codechecker_server $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_CLIENT)/codechecker_client $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CC_ANALYZER)/config/* $(CC_BUILD_DIR)/config && \
	cp -r $(CC_WEB)/config/* $(CC_BUILD_DIR)/config && \
	cp -r $(CC_SERVER)/config/* $(CC_BUILD_DIR)/config && \
	./scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/analyzer_version.json \
	  $(CC_BUILD_DIR)/config/web_version.json

	mkdir -p $(CC_BUILD_DIR)/cc_bin && \
	./scripts/build/create_commands.py -b $(BUILD_DIR) \
	  --cmd-dir codechecker_common/cmd \
	    $(CC_WEB)/codechecker_web/cmd \
	    $(CC_SERVER)/codechecker_server/cmd \
	    $(CC_CLIENT)/codechecker_client/cmd \
	    $(CC_ANALYZER)/codechecker_analyzer/cmd \
	  --bin-file $(ROOT)/bin/CodeChecker \
	  --cc-bin-file $(ROOT)/bin/CodeChecker.py

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

standalone_package: venv package
	# Create a version of the package, which uses a wrapper script to
	# eliminate the need to manually source the virtual environment before
	# using the CodeChecker runnable. Replaces the original main runnable
	# with a wrapper script of the same name. The package built this way
	# should be used just as the wrapped runnable, but without activating
	# the virtual environment beforehand.
	cd $(CC_BUILD_BIN_DIR) && \
	mv CodeChecker _CodeChecker && \
	$(ROOT)/scripts/build/wrap_binary_in_venv.py \
		-e $(ROOT)/venv \
		-b _CodeChecker \
		-o CodeChecker

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python3 venv && \
		$(ACTIVATE_RUNTIME_VENV) && \
		pip3 install -r $(CC_ANALYZER)/requirements.txt && \
		pip3 install -r $(CC_WEB)/requirements.txt

venv_osx:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python3 venv && \
		$(ACTIVATE_RUNTIME_VENV) && \
		pip3 install -r $(CC_ANALYZER)/requirements_py/osx/requirements.txt && \
		pip3 install -r $(CC_WEB)/requirements_py/osx/requirements.txt

clean_venv:
	rm -rf venv

PIP_DEV_DEPS_CMD = make -C $(CC_ANALYZER) pip_dev_deps && \
  make -C $(CC_WEB) pip_dev_deps && \
  make -C $(CC_TOOLS)/plist_to_html pip_dev_deps

pip_dev_deps:
	# Install the depencies for analyze, web and the tools.
	$(PIP_DEV_DEPS_CMD)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python3 venv_dev && \
		$(ACTIVATE_DEV_VENV) && $(PIP_DEV_DEPS_CMD)

clean_venv_dev:
	rm -rf venv_dev
	$(MAKE) -C $(CC_ANALYZER) clean_venv_dev
	$(MAKE) -C $(CC_WEB) clean_venv_dev
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean_venv_dev

clean: clean_package
	$(MAKE) -C $(CC_WEB) clean

clean_package: clean_plist_to_html clean_tu_collector clean_report_converter clean_report_hash clean_statistics_collector
	rm -rf $(BUILD_DIR)
	find . -name "*.pyc" -delete

clean_plist_to_html:
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean

clean_tu_collector:
	$(MAKE) -C $(CC_TOOLS)/tu_collector clean

clean_report_converter:
	$(MAKE) -C $(CC_TOOLS)/report-converter clean

clean_report_hash:
	$(MAKE) -C $(CC_TOOLS)/codechecker_report_hash clean

clean_statistics_collector:
	$(MAKE) -C $(CC_ANALYZER_TOOLS)/statistics_collector clean

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*

PYLINT_CMD = $(MAKE) -C $(CC_ANALYZER) pylint && \
  $(MAKE) -C $(CC_WEB) pylint && \
  pylint -j0 ./bin/** ./codechecker_common \
	./scripts/** ./scripts/build/** ./scripts/debug_tools/** \
	./scripts/gerrit_jenkins/** ./scripts/resources/** \
	./scripts/test/** \
	--rcfile=$(ROOT)/.pylintrc

pylint:
	PYLINTRC=$(ROOT)/.pylintrc $(PYLINT_CMD)

pylint_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_CMD)

PYCODE_CMD = $(MAKE) -C $(CC_ANALYZER) pycodestyle && \
	$(MAKE) -C $(CC_WEB) pycodestyle && \
	pycodestyle bin codechecker_common scripts

pycodestyle:
	$(PYCODE_CMD)

pycodestyle_in_env:
	$(ACTIVATE_DEV_VENV) && $(PYCODE_CMD)

test: test_analyzer test_web

test_in_env: test_analyzer_in_env test_web_in_env

test_analyzer:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test

test_analyzer_in_env:
	$(MAKE) -C $(CC_ANALYZER) test_in_env

# Run a specific analyzer test.
test_analyzer_feature:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) run_test

test_web:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test

# Run all the functional tests for the web with SQLite.
test_web_sqlite:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_sqlite

# Run all the functional tests for the web with psycopg2.
test_web_psql_psycopg2:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_psql_psycopg2

# Run all the functional tests for the web with pg8000.
test_web_psql_pg8000:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_psql_pg8000

# Run a specific web test.
test_web_feature:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) run_test

test_web_in_env:
	$(MAKE) -C $(CC_WEB) test_in_env

test_unit:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_unit
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_unit
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_COMMON)/tests/unit test_unit

test_unit_in_env:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_unit_in_env
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_unit_in_env

test_functional:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_functional
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_functional

test_functional_in_env:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_functional_in_env
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_functional_in_env

set_git_commit_template:
	if [ -d "$(CURRENT_DIR)/.git" ]; then git config --local commit.template .gitmessage; fi
