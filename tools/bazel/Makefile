# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
CURRENT_DIR = ${CURDIR}
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
PYTHON_BIN ?= python3
COMPILE_COMMANDS_DIR = $(BUILD_DIR)/bazel

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

default: all

all: package

venv:
	# Create a virtual environment which can be used to run the build package.
	python3 -m venv venv && $(ACTIVATE_RUNTIME_VENV)

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	python3 -m venv venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

include tests/Makefile

package:
	# Install package in 'development mode'.
	${PYTHON_BIN} setup.py develop

build:
	${PYTHON_BIN} setup.py build --build-purelib $(COMPILE_COMMANDS_DIR)

dist:
	# Create a source distribution.
	${PYTHON_BIN} setup.py sdist

upload_test:
	# Upload package to the TestPyPI repository.
	$(eval PKG_NAME := $(shell ${PYTHON_BIN} setup.py --name))
	$(eval PKG_VERSION := $(shell ${PYTHON_BIN} setup.py --version))
	twine upload -r testpypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

upload:
	# Upload package to the PyPI repository.
	$(eval PKG_NAME := $(shell ${PYTHON_BIN} setup.py --name))
	$(eval PKG_VERSION := $(shell ${PYTHON_BIN} setup.py --version))
	twine upload -r pypi dist/$(PKG_NAME)-$(PKG_VERSION).tar.gz

clean:
	rm -rf $(BUILD_DIR)
	rm -rf bazel_compile_commands.egg-info
