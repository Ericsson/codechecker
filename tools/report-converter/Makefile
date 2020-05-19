# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
CURRENT_DIR = $(shell pwd)
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
REPORT_CONVERTER_DIR = $(BUILD_DIR)/report_converter

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

default: all

all: package

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python3 venv && $(ACTIVATE_RUNTIME_VENV)

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python3 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

include tests/Makefile

package:
	# Install package in 'development mode'.
	python3 setup.py develop

build:
	python3 setup.py build --build-purelib $(REPORT_CONVERTER_DIR)

dist:
	# Create a source distribution.
	python3 setup.py sdist

upload_test:
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell python3 setup.py --name))
	$(eval PKG_VERSION := $(shell python3 setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload:
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell python3 setup.py --name))
	$(eval PKG_VERSION := $(shell python3 setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)
	rm -rf report_converter.egg-info
