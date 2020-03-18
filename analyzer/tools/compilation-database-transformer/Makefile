# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
CURRENT_DIR = $(shell pwd)
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
TRANSFORMER_TOOL_DIR = $(BUILD_DIR)/compilation_database_transformer

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt
VENV_PROD_REQ_FILE ?= requirements_py/prod/requirements.txt

default: all

all: package

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python3 venv && \
 		$(ACTIVATE_RUNTIME_VENV) && pip3 install -r $(VENV_PROD_REQ_FILE)

clean_venv:
	rm -rf venv

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python3 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

clean_venvs: clean_venv clean_venv_dev

include tests/Makefile

package:
	# Install package in 'development mode'.
	python3 setup.py develop

package_in_env: venv_dev
	# Install package in 'development mode'.
	$(ACTIVATE_DEV_VENV) && python3 setup.py develop


build:
	python3 setup.py build --build-purelib $(TRANSFORMER_TOOL_DIR)

build_in_env: venv_dev
	$(ACTIVATE_DEV_VENV) && python3 setup.py build --build-purelib $(TRANSFORMER_TOOL_DIR)

dist:
	# Create a source distribution.
	python3 setup.py sdist

dist_in_env: venv_dev
	# Create a source distribution.
	$(ACTIVATE_DEV_VENV) && python3 setup.py sdist

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
	rm -rf compilation_database_transformer.egg-info

