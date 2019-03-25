# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

CODEMIRROR = https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.30.0

CURRENT_DIR = $(shell pwd)
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
BIN_DIR ?= $(BUILD_DIR)/bin

STATIC_DIR = $(CURRENT_DIR)/plist_to_html/static
VENDOR_DIR = $(STATIC_DIR)/vendor
CODEMIRROR_DIR = $(VENDOR_DIR)/codemirror

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

include tests/Makefile

venv:
	# Create a virtual environment which can be used to run the build package.
	virtualenv -p python2 venv && $(ACTIVATE_RUNTIME_VENV)

venv_dev:
	# Create a virtual environment for development.
	virtualenv -p python2 venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

default: all

all: package

package: dep
	mkdir -p $(BIN_DIR)
	cp -r plist_to_html $(BUILD_DIR)
	ln -sf $(BUILD_DIR)/plist_to_html/PlistToHtml.py $(BIN_DIR)/plist-to-html

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

clean_vendor:
	rm -rf $(VENDOR_DIR)
