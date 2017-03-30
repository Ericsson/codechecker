-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build

# Root of the repository.
ROOT = $(CURRENT_DIR)

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

default: package

# Test running related targets.
include tests/Makefile

gen-docs: build_dir
	doxygen ./Doxyfile.in && \
	cp -a ./gen-docs $(BUILD_DIR)/gen-docs

thrift: build_dir

	if [ -d "$(BUILD_DIR)/gen-py" ]; then rm -rf $(BUILD_DIR)/gen-py; fi
	if [ -d "$(BUILD_DIR)/gen-js" ]; then rm -rf $(BUILD_DIR)/gen-js; fi

	thrift -r -o $(BUILD_DIR) -I api/ \
		--gen py api/report_storage_server.thrift

	thrift -r -o $(BUILD_DIR) -I api/ \
		--gen py --gen js:jquery api/report_viewer_server.thrift

	thrift -r -o $(BUILD_DIR) -I api/ \
		--gen py api/authentication.thrift

package: build_dir gen-docs thrift
	if [ ! -d "$(BUILD_DIR)/CodeChecker" ]; then \
		./scripts/build_package.py -r $(ROOT) -o $(BUILD_DIR) -b $(BUILD_DIR); \
	fi

travis:
	# Make TravisCI specific changes.
	scripts/change_clang_version.py $(CURRENT_DIR)

clean_travis:
	# Clean CodeChecker config files stored in the users home directory.
	rm -rf ~/.codechecker*

build_dir:
	mkdir -p $(BUILD_DIR)

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && pip install -r .ci/basic_python_requirements

clean_venv:
	rm -rf venv

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r .ci/python_requirements && \
		pip install -r tests/requirements.txt

clean_venv_dev:
	rm -rf venv_dev

clean:
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs

