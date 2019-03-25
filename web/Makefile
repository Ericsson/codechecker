-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(ROOT)/build

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

include tests/Makefile
include server/tests/Makefile

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

# TODO: add targets to build server separately.
