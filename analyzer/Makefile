-include Makefile.local

CURRENT_DIR = ${CURDIR}
BUILD_DIR ?= $(CURRENT_DIR)/build
PYTHON_BIN ?= python3

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python3

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

CC_TOOLS = $(ROOT)/tools

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

# Set it to YES if you would like to build and package 64 bit only shared
# objects and ldlogger binary.
BUILD_LOGGER_64_BIT_ONLY ?= NO

include tests/Makefile

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p ${PYTHON_BIN} venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	mkdir -p $(CC_BUILD_LIB_DIR)

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

build_merge_clang_extdef_mappings:
	$(MAKE) -C tools/merge_clang_extdef_mappings build

package_merge_clang_extdef_mappings: build_merge_clang_extdef_mappings package_dir_structure
	# Copy plist-to-html files.
	cp -r tools/merge_clang_extdef_mappings/build/merge_clang_extdef_mappings/codechecker_merge_clang_extdef_mappings $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_merge_clang_extdef_mappings/cli.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/codechecker_merge_clang_extdef_mappings/cli.py bin/merge-clang-extdef-mappings

build_statistics_collector:
	$(MAKE) -C $(CC_ANALYZER_TOOLS)/statistics_collector build

package_statistics_collector: build_statistics_collector package_dir_structure
	# Copy statistics-collector files.
	cp -r tools/statistics_collector/build/statistics_collector/codechecker_statistics_collector $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_statistics_collector/cli.py && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../lib/python3/codechecker_statistics_collector/cli.py bin/post-process-stats

# This target should be used from the top level Makefile to build the package
# together with the web part. This way we will not build plist-to-html
# multiple times.
package_analyzer: package_dir_structure

package: package_plist_to_html package_tu_collector package_analyzer package_merge_clang_extdef_mappings package_statistics_collector
	# Copy libraries.
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CURRENT_DIR)/codechecker_analyzer $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CURRENT_DIR)/config/* $(CC_BUILD_DIR)/config && \
	${PYTHON_BIN} $(ROOT)/scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/analyzer_version.json \

	# Copy CodeChecker entry point sub-commands.
	mkdir -p $(CC_BUILD_DIR)/cc_bin && \
	${PYTHON_BIN} $(ROOT)/scripts/build/create_commands.py -b $(BUILD_DIR) \
	  --cmd-dir codechecker_common/cmd \
	    $(CC_ANALYZER)/codechecker_analyzer/cmd \
	  --bin-file $(ROOT)/bin/CodeChecker \
	  --cc-bin-file $(ROOT)/bin/CodeChecker.py

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

package_ld_logger:
	mkdir -p $(CC_BUILD_DIR)/ld_logger && \
	mkdir -p $(CC_BUILD_DIR)/bin && \
	cp -r $(CURRENT_DIR)/tools/build-logger/build/* $(CC_BUILD_DIR)/ld_logger && \
	cd $(CC_BUILD_DIR) && \
	ln -sf ../ld_logger/bin/ldlogger bin/ldlogger

define LOGGER_BUILD_ERROR_MSG
Failed to compile logger for 32bit and 64bit targets please check if
gcc-multilib is installed if both targets are needed or set the
BUILD_LOGGER_64_BIT_ONLY=YES environment variable for a 64bit only build.
endef

export LOGGER_BUILD_ERROR_MSG
build_ld_logger:
ifeq ($(BUILD_LOGGER_64_BIT_ONLY),YES)
	$(MAKE) -C tools/build-logger -f Makefile.manual pack64bit_only 2> /dev/null
else
	$(MAKE) -C tools/build-logger -f Makefile.manual 2> /dev/null || (echo "$$LOGGER_BUILD_ERROR_MSG" && false)
endif

# NOTE: extra spaces are allowed and ignored at the beginning of the
# conditional directive line, but a tab is not allowed.
ifeq ($(OS),Windows_NT)
  $(info Skipping ld logger from package)
else
  UNAME_S ?= $(shell uname -s)
  ifeq ($(UNAME_S),Linux)
    package_ld_logger: build_ld_logger
    package_analyzer: package_ld_logger
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
