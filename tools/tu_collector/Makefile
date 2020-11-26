# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin

PYTHON_BIN ?= python3
TU_COLLECTOR_DIR = $(BUILD_DIR)/tu_collector

ACTIVATE_VENV ?= . venv/bin/activate

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p ${PYTHON_BIN} venv && $(ACTIVATE_VENV)

default: all

all: package

package:
	# Install package in 'development mode'.
	${PYTHON_BIN} setup.py develop

build:
	${PYTHON_BIN} setup.py build --build-purelib $(TU_COLLECTOR_DIR)

dist:
	# Create a source distribution.
	${PYTHON_BIN} setup.py sdist

upload_test: dist
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell ${PYTHON_BIN} setup.py --name))
	$(eval PKG_VERSION := $(shell ${PYTHON_BIN} setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload: dist
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell ${PYTHON_BIN} setup.py --name))
	$(eval PKG_VERSION := $(shell ${PYTHON_BIN} setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)

test:
	REPO_ROOT=$(REPO_ROOT) nosetests tests
