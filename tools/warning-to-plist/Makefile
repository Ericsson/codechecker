# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
CURRENT_DIR = $(shell pwd)
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
WARNING_TO_PLIST_DIR = $(BUILD_DIR)/warning_to_plist

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

default: all

all: package

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && $(ACTIVATE_RUNTIME_VENV)

pip_dev_deps:
	pip install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

package:
	# Install package in 'development mode'.
	python setup.py develop

build:
	python setup.py build --build-purelib $(WARNING_TO_PLIST_DIR)

dist:
	# Create a source distribution.
	python setup.py sdist

upload_test:
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload:
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)
	rm -rf warning_to_plist.egg-info
