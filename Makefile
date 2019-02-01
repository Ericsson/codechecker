-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build

# Root of the repository.
ROOT = $(CURRENT_DIR)

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_REQ_FILE ?= requirements_py/requirements.txt
VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

OSX_VENV_REQ_FILE ?= requirements_py/osx/requirements.txt

default: package

# Test running related targets.
include tests/Makefile

gen-docs: build_dir
	doxygen ./Doxyfile.in && \
	cp -a ./gen-docs $(BUILD_DIR)/gen-docs

thrift: build_dir

	if [ -d "$(BUILD_DIR)/thrift" ]; then rm -rf $(BUILD_DIR)/thrift; fi

	mkdir $(BUILD_DIR)/thrift

	BUILD_DIR=$(BUILD_DIR) $(MAKE) -C api/

userguide: build_dir
	$(MAKE) -C www/userguide

package: clean_package build_dir gen-docs thrift userguide build_plist_to_html build_tu_collector
	./scripts/build_package.py -r $(ROOT) -o $(BUILD_DIR) -b $(BUILD_DIR)

build_dir:
	mkdir -p $(BUILD_DIR)

build_plist_to_html:
	$(MAKE) -C vendor/plist_to_html

build_tu_collector:
	$(MAKE) -C vendor/tu_collector

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && pip install -r $(VENV_REQ_FILE)

venv_osx:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && \
		$(ACTIVATE_RUNTIME_VENV) && pip install -r $(OSX_VENV_REQ_FILE)

clean_venv:
	rm -rf venv

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE) && \
		pip install -r requirements_py/test/requirements.txt

clean_venv_dev:
	rm -rf venv_dev

clean: clean_package clean_vendor

clean_package: clean_userguide clean_plist_to_html clean_tu_collector
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs
	find . -name "*.pyc" -delete

clean_vendor:
	rm -rf vendor/codemirror
	rm -rf vendor/dojotoolkit
	rm -rf vendor/fonts
	rm -rf vendor/highlightjs
	rm -rf vendor/jsplumb
	rm -rf vendor/marked
	rm -rf vendor/thrift

clean_userguide:
	rm -rf www/userguide/gen-docs

clean_plist_to_html:
	rm -rf vendor/plist_to_html/build

clean_tu_collector:
	rm -rf vendor/tu_collector/build
