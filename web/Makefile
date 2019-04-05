-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR ?= $(CURRENT_DIR)/build

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_WEB_DIR = $(CC_BUILD_DIR)/www
CC_BUILD_PLUGIN_DIR = $(CC_BUILD_DIR)/plugin
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python2.7
CC_BUILD_DOCS_DIR = $(CC_BUILD_WEB_DIR)/docs
CC_BUILD_SCRIPTS_DIR = $(CC_BUILD_WEB_DIR)/scripts
CC_BUILD_API_DIR = $(CC_BUILD_SCRIPTS_DIR)/codechecker-api
CC_BUILD_WEB_PLUGINS_DIR = $(CC_BUILD_SCRIPTS_DIR)/plugins
CC_BUILD_GEN_DIR = $(CC_BUILD_LIB_DIR)/codechecker_api

CC_SERVER = $(CURRENT_DIR)/server/
CC_CLIENT = $(CURRENT_DIR)/client/

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

CC_TOOLS = $(ROOT)/tools

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

include tests/Makefile
include server/tests/Makefile

pip_dev_deps:
	pip install -r $(VENV_DEV_REQ_FILE)

thrift: build_dir
	if [ -d "$(BUILD_DIR)/thrift" ]; then rm -rf $(BUILD_DIR)/thrift; fi
	mkdir $(BUILD_DIR)/thrift
	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C $(CURRENT_DIR)/api/

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

build_dir:
	mkdir -p $(BUILD_DIR)

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	mkdir -p $(CC_BUILD_LIB_DIR)

package_thrift: thrift package_dir_structure
	mkdir -p $(CC_BUILD_API_DIR) && \
	mkdir -p $(CC_BUILD_GEN_DIR) && \
	cp -r $(BUILD_DIR)/thrift/v*/gen-py/* $(CC_BUILD_GEN_DIR) && \
	cp -r $(BUILD_DIR)/thrift/v*/gen-js/* $(CC_BUILD_API_DIR)

gen_docs: build_dir
	cd $(ROOT) && \
	doxygen $(ROOT)/Doxyfile.in && \
	cp -a $(ROOT)/gen-docs $(BUILD_DIR)/gen-docs

package_docs: gen_docs
	mkdir -p $(CC_BUILD_DOCS_DIR) && \
	mkdir -p $(CC_BUILD_DOCS_DIR)/checker_md_docs && \
	cp -r $(BUILD_DIR)/gen-docs/html/* $(CC_BUILD_DOCS_DIR) && \
	cp -r $(ROOT)/docs/web/checker_docs/* $(CC_BUILD_DOCS_DIR)/checker_md_docs/

	# Rename gen-docs to doc.
	rm -rf $(CC_BUILD_WEB_DIR)/userguide/doc && \
	mv $(CC_BUILD_WEB_DIR)/userguide/gen-docs $(CC_BUILD_WEB_DIR)/userguide/doc

gen_userguide:
	mkdir -p $(CC_BUILD_WEB_DIR) && \
	$(MAKE) -C $(CC_SERVER)/www/userguide

package_www: package_dir_structure
	cp -r $(CC_SERVER)/www/* $(CC_BUILD_WEB_DIR)

package_userguide: gen_userguide package_www
	mkdir -p $(CC_BUILD_WEB_DIR)/images && \
	mv $(CC_BUILD_WEB_DIR)/userguide/images/* $(CC_BUILD_WEB_DIR)/images && \
	rm -rf $(CC_BUILD_WEB_DIR)/userguide/images

package_vendor: package_dir_structure
	$(MAKE) -C $(CC_SERVER)/vendor build BUILD_DIR=$(CC_BUILD_WEB_PLUGINS_DIR)

# This target should be used from the top level Makefile to build the package
# together with the analyzer part. This way we will not build plist-to-html
# multiple times.
package_web: package_thrift package_userguide package_vendor package_docs

build_plist_to_html:
	$(MAKE) -C $(ROOT)/tools/plist_to_html build

package_plist_to_html: build_plist_to_html package_dir_structure
	# Copy plist-to-html files.
	cp -r $(CC_TOOLS)/plist_to_html/build/plist_to_html/plist_to_html $(CC_BUILD_LIB_DIR)

package: package_plist_to_html package_web
	# Copy libraries.
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CURRENT_DIR)/codechecker_web $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_SERVER)/codechecker_server $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_CLIENT)/codechecker_client $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CURRENT_DIR)/config/* $(CC_BUILD_DIR)/config && \
	cp -r $(CC_SERVER)/config/* $(CC_BUILD_DIR)/config && \
	$(ROOT)/scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/web_version.json

	# Copy CodeChecker entry point sub-commands.
	mkdir -p $(CC_BUILD_DIR)/cc_bin && \
	$(ROOT)/scripts/build/create_commands.py -b $(BUILD_DIR) \
	  $(ROOT)/bin:codechecker_common/cmd \
	  $(CURRENT_DIR)/bin:codechecker_web/cmd \
	  $(CC_SERVER)/bin:codechecker_server/cmd \
	  $(CC_CLIENT)/bin:codechecker_client/cmd

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

clean_package: clean_userguide clean_plist_to_html
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs
	find . -name "*.pyc" -delete

clean_userguide:
	rm -rf www/userguide/gen-docs

clean_plist_to_html:
	rm -rf $(ROOT)/tools/plist_to_html/build
