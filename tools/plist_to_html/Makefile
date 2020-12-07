# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

CODEMIRROR = https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.30.0

PYTHON_BIN ?= python3
CURRENT_DIR = ${CURDIR}
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
PLIST_TO_HTML_DIR = $(BUILD_DIR)/plist_to_html

STATIC_DIR = $(CURRENT_DIR)/plist_to_html/static
VENDOR_DIR = $(STATIC_DIR)/vendor
CODEMIRROR_DIR = $(VENDOR_DIR)/codemirror


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

package: dep
	# Install package in 'development mode'.
	${PYTHON_BIN} setup.py develop

build: dep
	${PYTHON_BIN} setup.py build --build-purelib $(PLIST_TO_HTML_DIR)

dist: dep
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

vendor_dir:
	mkdir -p $(VENDOR_DIR)

codemirror_dir: vendor_dir
	mkdir -p $ $(CODEMIRROR_DIR)

dep: codemirror

codemirror: $(CODEMIRROR_DIR)/codemirror.min.js
codemirror: $(CODEMIRROR_DIR)/codemirror.min.css
codemirror: $(CODEMIRROR_DIR)/codemirror.LICENSE
codemirror: $(CODEMIRROR_DIR)/clike.min.js

$(CODEMIRROR_DIR)/codemirror.min.js: codemirror_dir
	[ -f $(CODEMIRROR_DIR)/codemirror.min.js ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/codemirror.min.js \
			 -z $(CODEMIRROR_DIR)/codemirror.min.js \
			 -o $(CODEMIRROR_DIR)/codemirror.min.js

$(CODEMIRROR_DIR)/codemirror.min.css: codemirror_dir
	[ -f $(CODEMIRROR_DIR)/codemirror.min.css ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/codemirror.min.css \
			 -z $(CODEMIRROR_DIR)/codemirror.min.css \
			 -o $(CODEMIRROR_DIR)/codemirror.min.css

$(CODEMIRROR_DIR)/codemirror.LICENSE: codemirror_dir
	[ -f $(CODEMIRROR_DIR)/codemirror.LICENSE ] && : || \
	curl -sSfLk --get https://raw.githubusercontent.com/codemirror/CodeMirror/master/LICENSE \
			 -z $(CODEMIRROR_DIR)/codemirror.LICENSE \
			 -o $(CODEMIRROR_DIR)/codemirror.LICENSE

$(CODEMIRROR_DIR)/clike.min.js: codemirror_dir
	[ -f $(CODEMIRROR_DIR)/clike.min.js ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/mode/clike/clike.min.js \
			 -z $(CODEMIRROR_DIR)/clike.min.js \
			 -o $(CODEMIRROR_DIR)/clike.min.js

clean:
	rm -rf $(BUILD_DIR)
	rm -rf dist
	rm -rf plist_to_html.egg-info

clean_vendor:
	rm -rf $(VENDOR_DIR)
