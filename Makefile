-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build

# Root of the repository.
ROOT = $(CURRENT_DIR)

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_REQ_FILE ?= .ci/basic_python_requirements
VENV_DEV_REQ_FILE ?= .ci/python_requirements

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
		--gen py --gen js:jquery api/report_server.thrift

	thrift -r -o $(BUILD_DIR) -I api/ \
		--gen py --gen js:jquery api/authentication.thrift

	thrift -r -o $(BUILD_DIR) -I api/ \
		--gen py --gen js:jquery api/products.thrift

package: build_dir gen-docs thrift
	if [ ! -d "$(BUILD_DIR)/CodeChecker" ]; then \
		./scripts/build_package.py -r $(ROOT) -o $(BUILD_DIR) -b $(BUILD_DIR); \
	fi

build_dir:
	mkdir -p $(BUILD_DIR)

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && pip install -r $(VENV_REQ_FILE)

clean_venv:
	rm -rf venv

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE) && \
		pip install -r tests/requirements.txt

clean_venv_dev:
	rm -rf venv_dev

clean: clean_package clean_vendor

clean_package:
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs

clean_vendor:
	rm -rf vendor/codemirror
	rm -rf vendor/dojotoolkit
	rm -rf vendor/fonts
	rm -rf vendor/highlightjs
	rm -rf vendor/jsplumb
	rm -rf vendor/marked
	rm -rf vendor/thrift
