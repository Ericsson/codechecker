-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build
VENDOR_DIR = $(CURRENT_DIR)/vendor

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_BIN_DIR = $(CC_BUILD_DIR)/bin
CC_BUILD_WEB_DIR = $(CC_BUILD_DIR)/www
CC_BUILD_PLUGIN_DIR = $(CC_BUILD_DIR)/plugin
CC_BUILD_SCRIPTS_DIR = $(CC_BUILD_WEB_DIR)/scripts
CC_BUILD_DOCS_DIR = $(CC_BUILD_WEB_DIR)/docs
CC_BUILD_WEB_PLUGINS_DIR = $(CC_BUILD_SCRIPTS_DIR)/plugins
CC_BUILD_API_DIR = $(CC_BUILD_SCRIPTS_DIR)/codechecker-api
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python2.7
CC_BUILD_GEN_DIR = $(CC_BUILD_LIB_DIR)/codechecker_api

CC_WEB = $(CURRENT_DIR)/web
CC_SERVER = $(CC_WEB)/server/
CC_CLIENT = $(CC_WEB)/client/
CC_ANALYZER = $(CURRENT_DIR)/analyzer

CC_TOOLS = $(CURRENT_DIR)/tools

# Root of the repository.
ROOT = $(CURRENT_DIR)

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

default: package

gen-docs: build_dir
	doxygen ./Doxyfile.in && \
	cp -a ./gen-docs $(BUILD_DIR)/gen-docs

thrift: build_dir

	if [ -d "$(BUILD_DIR)/thrift" ]; then rm -rf $(BUILD_DIR)/thrift; fi

	mkdir $(BUILD_DIR)/thrift

	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB)/api/

userguide: build_dir
	$(MAKE) -C $(CC_SERVER)/www/userguide

package: clean_package build_dir gen-docs thrift userguide build_plist_to_html build_tu_collector build_vendor
	# Create directory structure.
	mkdir -p $(CC_BUILD_BIN_DIR) && \
	mkdir -p $(CC_BUILD_LIB_DIR) && \
	mkdir -p $(CC_BUILD_PLUGIN_DIR)

	# Copy plist-to-html files.
	cp -r $(CC_TOOLS)/plist_to_html/build/plist_to_html/plist_to_html $(CC_BUILD_LIB_DIR)

	# Copy tu_collector files.
	cp -r $(CC_TOOLS)/tu_collector/build/tu_collector/tu_collector $(CC_BUILD_LIB_DIR)

	# Copy generated thrift files.
	mkdir -p $(CC_BUILD_GEN_DIR) && \
	mkdir -p $(CC_BUILD_API_DIR) && \
	cp -r $(BUILD_DIR)/thrift/v*/gen-py/* $(CC_BUILD_GEN_DIR) && \
	cp -r $(BUILD_DIR)/thrift/v*/gen-js/* $(CC_BUILD_API_DIR)

	# Copy libraries.
	mkdir -p $(CC_BUILD_LIB_DIR)/codechecker && \
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_ANALYZER)/codechecker_analyzer $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_WEB)/codechecker_web $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_SERVER)/codechecker_server $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_CLIENT)/codechecker_client $(CC_BUILD_LIB_DIR)

	# Copy sub-commands.
	cp $(ROOT)/bin/* $(CC_BUILD_DIR)/bin && \
	cp $(CC_ANALYZER)/bin/* $(CC_BUILD_DIR)/bin

	# Copy documentation files.
	mkdir -p $(CC_BUILD_DOCS_DIR) && \
	mkdir -p $(CC_BUILD_DOCS_DIR)/checker_md_docs && \
	cp -r $(BUILD_DIR)/gen-docs/html/* $(CC_BUILD_DOCS_DIR) && \
	cp -r $(ROOT)/docs/web/checker_docs/* $(CC_BUILD_DOCS_DIR)/checker_md_docs/

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
		$(ROOT)/bin:codechecker_common/cmd \
		$(CC_WEB)/bin:codechecker_web/cmd \
		$(CC_SERVER)/bin:codechecker_server/cmd \
		$(CC_CLIENT)/bin:codechecker_client/cmd \
		$(CC_ANALYZER)/bin:codechecker_analyzer/cmd

	# Copy web client files.
	mkdir -p $(CC_BUILD_WEB_DIR) && \
	cp -r $(CC_SERVER)/www/* $(CC_BUILD_WEB_DIR) && \
	mv $(CC_BUILD_WEB_DIR)/userguide/images/* $(CC_BUILD_WEB_DIR)/images && \
	rm -rf $(CC_BUILD_WEB_DIR)/userguide/images

	# Rename gen-docs to doc.
	mv $(CC_BUILD_WEB_DIR)/userguide/gen-docs $(CC_BUILD_WEB_DIR)/userguide/doc

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

package_ld_logger:
	mkdir -p $(CC_BUILD_DIR)/ld_logger && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	cp -r $(CC_ANALYZER)/tools/build-logger/build/* $(CC_BUILD_DIR)/ld_logger && \
	ln -s $(CC_BUILD_DIR)/ld_logger/bin/ldlogger $(CC_BUILD_DIR)/bin/ldlogger

build_ld_logger:
	$(MAKE) -C $(CC_ANALYZER)/tools/build-logger -f Makefile.manual 2> /dev/null

build_ld_logger_x86:
	$(MAKE) -C $(CC_ANALYZER)/tools/build-logger -f Makefile.manual pack32bit 2> /dev/null

build_ld_logger_x64:
	$(MAKE) -C $(CC_ANALYZER)/tools/build-logger -f Makefile.manual pack64bit 2> /dev/null

# NOTE: extra spaces are allowed and ignored at the beginning of the
# conditional directive line, but a tab is not allowed.
ifeq ($(OS),Windows_NT)
  $(info Skipping ld logger from package)
else
  UNAME_S ?= $(shell uname -s)
  ifeq ($(UNAME_S),Linux)
    UNAME_P ?= $(shell uname -p)
    ifeq ($(UNAME_P),x86_64)
      package_ld_logger: build_ld_logger_x64
      package: package_ld_logger
    else ifneq ($(filter %86,$(UNAME_P)),)
      package_ld_logger: build_ld_logger_x86
      package: package_ld_logger
    else
      package_ld_logger: build_ld_logger
      package: package_ld_logger
    endif
  else ifeq ($(UNAME_S),Darwin)
    ifeq (, $(shell which intercept-build))
      $(error "No intercept-build (scan-build-py) in $(PATH).")
    endif
  endif
endif

build_vendor:
	$(MAKE) -C $(CC_SERVER)/vendor build BUILD_DIR=$(CC_BUILD_WEB_PLUGINS_DIR)

build_dir:
	mkdir -p $(BUILD_DIR)

build_plist_to_html:
	$(MAKE) -C $(CC_TOOLS)/plist_to_html build

build_tu_collector:
	$(MAKE) -C $(CC_TOOLS)/tu_collector build

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && \
		pip install -r $(CC_ANALYZER)/requirements.txt && \
		pip install -r $(CC_WEB)/requirements.txt

venv_osx:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && \
		pip install -r $(CC_ANALYZER)/requirements_py/osx/requirements.txt && \
		pip install -r $(CC_WEB)/requirements_py/osx/requirements.txt

clean_venv:
	rm -rf venv

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && \
		pip install -r $(CC_ANALYZER)/requirements_py/dev/requirements.txt && \
		pip install -r $(CC_ANALYZER)/requirements_py/test/requirements.txt && \
		pip install -r $(CC_WEB)/requirements_py/dev/requirements.txt && \
		pip install -r $(CC_WEB)/requirements_py/test/requirements.txt && \
		pip install -r $(CC_TOOLS)/plist_to_html/requirements_py/test/requirements.txt

clean_venv_dev:
	rm -rf venv_dev
	$(MAKE) -C $(CC_ANALYZER) clean_venv_dev
	$(MAKE) -C $(CC_WEB) clean_venv_dev
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean_venv_dev

clean: clean_package clean_vendor

clean_package: clean_userguide clean_plist_to_html clean_tu_collector
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs
	find . -name "*.pyc" -delete

clean_vendor:
	$(MAKE) -C $(CC_SERVER)/vendor clean_vendor

clean_userguide:
	rm -rf www/userguide/gen-docs

clean_plist_to_html:
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean

clean_tu_collector:
	$(MAKE) -C $(CC_TOOLS)/tu_collector clean

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*

pylint: venv_dev
	$(MAKE) -C $(CC_ANALYZER) pylint && \
	$(MAKE) -C $(CC_WEB) pylint && \
	pylint ./bin ./codechecker_common ./scripts \
	  --disable=all \
	  --enable=logging-format-interpolation,old-style-class

pycodestyle: venv_dev
	$(MAKE) -C $(CC_ANALYZER) pycodestyle && \
	$(MAKE) -C $(CC_WEB) pycodestyle && \
	pycodestyle bin codechecker_common scripts

test: test_analyzer test_server

test_analyzer:
	$(MAKE) -C $(CC_ANALYZER) test

test_server:
	$(MAKE) -C $(CC_WEB) test

test_unit:
	$(MAKE) -C $(CC_ANALYZER) test_unit
	$(MAKE) -C $(CC_WEB) test_unit

test_unit_novenv:
	$(MAKE) -C $(CC_ANALYZER) test_unit_novenv
	$(MAKE) -C $(CC_WEB) test_unit_novenv

test_functional: package
	$(MAKE) -C $(CC_ANALYZER) test_functional
	$(MAKE) -C $(CC_WEB) test_functional

test_functional_novenv: package
	$(MAKE) -C $(CC_ANALYZER) test_functional_novenv
	$(MAKE) -C $(CC_WEB) test_functional_novenv
