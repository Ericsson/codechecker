-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR ?= $(CURRENT_DIR)/build

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python2.7

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

include tests/Makefile

pip_dev_deps:
	pip install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	mkdir -p $(CC_BUILD_LIB_DIR)

build_plist_to_html:
	$(MAKE) -C $(ROOT)/tools/plist_to_html

package_plist_to_html: build_plist_to_html package_dir_structure
	# Copy plist-to-html files.
	cp -r $(ROOT)/tools/plist_to_html/plist_to_html $(CC_BUILD_LIB_DIR) && \
	cp -r $(ROOT)/tools/plist_to_html/build $(CC_BUILD_DIR)/plist_to_html && \
	ln -sf $(CC_BUILD_DIR)/plist_to_html/bin/plist-to-html $(CC_BUILD_DIR)/bin/plist-to-html

build_tu_collector:
	$(MAKE) -C $(ROOT)/tools/tu_collector

package_tu_collector: build_tu_collector package_dir_structure
	# Copy tu_collector files.
	cp -r $(ROOT)/tools/tu_collector/tu_collector $(CC_BUILD_LIB_DIR) && \
	cp -r $(ROOT)/tools/tu_collector/build $(CC_BUILD_DIR)/tu_collector && \
	ln -sf $(CC_BUILD_DIR)/tu_collector/bin/tu-collector $(CC_BUILD_DIR)/bin/tu-collector

# This target should be used from the top level Makefile to build the package
# together with the web part. This way we will not build plist-to-html
# multiple times.
package_analyzer: package_dir_structure

package: package_plist_to_html package_tu_collector package_analyzer
	# Copy libraries.
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CURRENT_DIR)/codechecker_analyzer $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CURRENT_DIR)/config/* $(CC_BUILD_DIR)/config && \
	$(ROOT)/scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/analyzer_version.json \

	# Copy CodeChecker entry point sub-commands.
	mkdir -p $(CC_BUILD_DIR)/cc_bin && \
	$(ROOT)/scripts/build/create_commands.py -b $(BUILD_DIR) \
	  $(ROOT)/bin:codechecker_common/cmd \
	  $(CURRENT_DIR)/bin:codechecker_analyzer/cmd

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

package_ld_logger:
	mkdir -p $(CC_BUILD_DIR)/ld_logger && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	cp -r $(CURRENT_DIR)/tools/build-logger/build/* $(CC_BUILD_DIR)/ld_logger && \
	ln -sf $(CC_BUILD_DIR)/ld_logger/bin/ldlogger $(CC_BUILD_DIR)/bin/ldlogger

build_ld_logger:
	$(MAKE) -C tools/build-logger -f Makefile.manual 2> /dev/null

build_ld_logger_x86:
	$(MAKE) -C tools/build-logger -f Makefile.manual pack32bit 2> /dev/null

build_ld_logger_x64:
	$(MAKE) -C tools/build-logger -f Makefile.manual pack64bit 2> /dev/null

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
      package_analyzer: package_ld_logger
    else ifneq ($(filter %86,$(UNAME_P)),)
      package_ld_logger: build_ld_logger_x86
      package_analyzer: package_ld_logger
    else
      package_ld_logger: build_ld_logger
      package_analyzer: package_ld_logger
    endif
  else ifeq ($(UNAME_S),Darwin)
    ifeq (, $(shell which intercept-build))
      $(info "No intercept-build (scan-build-py) in $(PATH).")
    endif
  endif
endif

clean_package: clean_plist_to_html clean_tu_collector
	rm -rf $(BUILD_DIR)
	find . -name "*.pyc" -delete

clean_plist_to_html:
	rm -rf $(ROOT)/tools/plist_to_html/build

clean_tu_collector:
	rm -rf $(ROOT)/tools/tu_collector/build
