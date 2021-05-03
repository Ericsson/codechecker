-include Makefile.local

CURRENT_DIR = ${CURDIR}
BUILD_DIR ?= $(CURRENT_DIR)/build
PYTHON_BIN ?= python3

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_BIN_DIR = $(CC_BUILD_DIR)/bin
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python3

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

CC_TOOLS = $(ROOT)/tools
CC_ANALYZER = $(ROOT)/analyzer

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_REQ_FILE ?= requirements.txt
VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

# Set it to YES if you would like to build and package 64 bit only shared
# objects and ldlogger binary.
BUILD_LOGGER_64_BIT_ONLY ?= NO

include tests/Makefile

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv:
	# Create a virtual environment which can be used to run the build package.
	python3 -m venv venv --prompt="CodeChecker analyze venv" && \
		$(ACTIVATE_RUNTIME_VENV) && pip3 install -r $(VENV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	python3 -m venv venv_dev --prompt="CodeChecker analyze venv-dev" && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv:
	rm -rf venv

clean_venv_dev:
	rm -rf venv_dev

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_BIN_DIR) && \
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
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/tu_collector/tu_collector.py tu_collector

build_report_hash:
	$(MAKE) -C $(CC_TOOLS)/codechecker_report_hash build

package_report_hash: build_report_hash package_dir_structure
	cp -rp $(CC_TOOLS)/codechecker_report_hash/build/codechecker_report_hash/codechecker_report_hash $(CC_BUILD_LIB_DIR)

build_report_converter:
	$(MAKE) -C $(CC_TOOLS)/report-converter build

package_report_converter: build_report_converter package_dir_structure
	cp -rp $(CC_TOOLS)/report-converter/build/report_converter/codechecker_report_converter $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_report_converter/cli.py && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/codechecker_report_converter/cli.py report-converter

build_merge_clang_extdef_mappings:
	$(MAKE) -C $(CC_ANALYZER)/tools/merge_clang_extdef_mappings build

package_merge_clang_extdef_mappings: build_merge_clang_extdef_mappings package_dir_structure
	# Copy plist-to-html files.
	cp -r tools/merge_clang_extdef_mappings/build/merge_clang_extdef_mappings/codechecker_merge_clang_extdef_mappings $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_merge_clang_extdef_mappings/cli.py && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/codechecker_merge_clang_extdef_mappings/cli.py merge-clang-extdef-mappings

build_statistics_collector:
	$(MAKE) -C $(CC_ANALYZER)/tools/statistics_collector build

package_statistics_collector: build_statistics_collector package_dir_structure
	# Copy statistics-collector files.
	cp -r tools/statistics_collector/build/statistics_collector/codechecker_statistics_collector $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_statistics_collector/cli.py && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/codechecker_statistics_collector/cli.py post-process-stats

build_bazel_compile_commands:
	$(MAKE) -C $(ROOT)/tools/bazel build

package_bazel_compile_commands: build_bazel_compile_commands package_dir_structure
	# Copy bazel_compile_commands files.
	cp -rp $(CC_TOOLS)/bazel/build/bazel/bazel_compile_commands $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/bazel_compile_commands/bazel_compile_commands.py && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/bazel_compile_commands/bazel_compile_commands.py bazel-compile-commands

# This target should be used from the top level Makefile to build the package
# together with the web part. This way we will not build plist-to-html
# multiple times.
package_analyzer: package_dir_structure package_plist_to_html package_tu_collector package_report_hash package_merge_clang_extdef_mappings package_report_converter package_statistics_collector package_bazel_compile_commands

package: package_analyzer
	# Copy libraries.
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CURRENT_DIR)/codechecker_analyzer $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CURRENT_DIR)/config/* $(CC_BUILD_DIR)/config && \
	${PYTHON_BIN} $(ROOT)/scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/analyzer_version.json \

	# Copy CodeChecker entry point sub-commands.
	${PYTHON_BIN} $(ROOT)/scripts/build/create_commands.py -b $(BUILD_DIR) \
	  --cmd-dir $(ROOT)/codechecker_common/cmd \
	    $(CC_ANALYZER)/codechecker_analyzer/cmd \
	  --bin-file $(ROOT)/bin/CodeChecker

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

standalone_package: venv package
	cd $(CC_BUILD_BIN_DIR) && \
	mv CodeChecker _CodeChecker && \
	${PYTHON_BIN} $(ROOT)/scripts/build/wrap_binary_in_venv.py \
		-e $(CURRENT_DIR)/venv \
		-b _CodeChecker \
		-o CodeChecker

package_ld_logger:
	mkdir -p $(CC_BUILD_DIR)/ld_logger && \
	mkdir -p $(CC_BUILD_BIN_DIR) && \
	cp -r $(CURRENT_DIR)/tools/build-logger/build/* $(CC_BUILD_DIR)/ld_logger && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../ld_logger/bin/ldlogger ldlogger

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

clean_package: clean_plist_to_html clean_tu_collector clean_bazel_compile_commands
	rm -rf $(BUILD_DIR)
	find . -name "*.pyc" -delete

clean_plist_to_html:
	rm -rf $(ROOT)/tools/plist_to_html/build

clean_tu_collector:
	rm -rf $(ROOT)/tools/tu_collector/build

clean_bazel_compile_commands:
	rm -rf $(ROOT)/tools/bazel/build
