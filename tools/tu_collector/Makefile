# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin

TU_COLLECTOR_DIR = $(BUILD_DIR)/tu_collector

ACTIVATE_VENV ?= . venv/bin/activate

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && $(ACTIVATE_VENV)

default: all

all: package

package:
	# Install package in 'development mode'.
	python setup.py develop

build:
	python setup.py build --build-purelib $(TU_COLLECTOR_DIR)

dist:
	# Create a source distribution.
	python setup.py sdist

upload_test: dist
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload: dist
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell python setup.py --name))
	$(eval PKG_VERSION := $(shell python setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)

test:
	REPO_ROOT=$(REPO_ROOT) nosetests tests
