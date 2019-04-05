-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build
VENDOR_DIR = $(CURRENT_DIR)/vendor

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_BIN_DIR = $(CC_BUILD_DIR)/bin
CC_BUILD_WEB_DIR = $(CC_BUILD_DIR)/www
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python2.7

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
	cp -r $(CC_TOOLS)/tu_collector/build/tu_collector/tu_collector $(CC_BUILD_LIB_DIR)

package: package_dir_structure package_plist_to_html package_tu_collector
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) package_analyzer
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
		$(ROOT)/bin:codechecker_common/cmd \
		$(CC_WEB)/bin:codechecker_web/cmd \
		$(CC_SERVER)/bin:codechecker_server/cmd \
		$(CC_CLIENT)/bin:codechecker_client/cmd \
		$(CC_ANALYZER)/bin:codechecker_analyzer/cmd

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

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

PIP_DEV_DEPS_CMD = make -C $(CC_ANALYZER) pip_dev_deps && \
  make -C $(CC_WEB) pip_dev_deps && \
  make -C $(CC_TOOLS)/plist_to_html pip_dev_deps

pip_dev_deps:
	# Install the depencies for analyze, web and the tools.
	$(PIP_DEV_DEPS_CMD)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && $(PIP_DEV_DEPS_CMD)

clean_venv_dev:
	rm -rf venv_dev
	$(MAKE) -C $(CC_ANALYZER) clean_venv_dev
	$(MAKE) -C $(CC_WEB) clean_venv_dev
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean_venv_dev

clean: clean_package clean_vendor

clean_package: clean_plist_to_html clean_tu_collector
	rm -rf $(BUILD_DIR)
	find . -name "*.pyc" -delete

clean_vendor:
	$(MAKE) -C $(CC_SERVER)/vendor clean_vendor

clean_plist_to_html:
	$(MAKE) -C $(CC_TOOLS)/plist_to_html clean

clean_tu_collector:
	$(MAKE) -C $(CC_TOOLS)/tu_collector clean

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*

PYLINT_CMD = $(MAKE) -C $(CC_ANALYZER) pylint && \
  $(MAKE) -C $(CC_WEB) pylint && \
  pylint ./bin ./codechecker_common ./scripts \
    --disable=all \
    --enable=logging-format-interpolation,old-style-class

pylint:
	$(PYLINT_CMD)

pylint_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && $(PYLINT_CMD)

PYCODE_CMD = $(MAKE) -C $(CC_ANALYZER) pycodestyle && \
	$(MAKE) -C $(CC_WEB) pycodestyle && \
	pycodestyle bin codechecker_common scripts

pycodestyle:
	$(PYCODE_CMD)

pycodestyle_in_env:
	$(ACTIVATE_DEV_VENV) && $(PYCODE_CMD)

test: test_analyzer test_server

test_analyzer:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test

test_analyzer_in_env:
	$(MAKE) -C $(CC_ANALYZER) test_in_env

test_server:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test

test_server_in_env:
	$(MAKE) -C $(CC_WEB) test_in_env

test_unit:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_unit
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_unit

test_unit_in_env:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_unit_in_env
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_unit_in_env

test_functional:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_functional
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_functional

test_functional_in_env:
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_ANALYZER) test_functional_in_env
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CC_WEB) test_functional_in_env
