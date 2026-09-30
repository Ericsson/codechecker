# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
CODEMIRROR = https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.30.0
CODEMIRROR_DIR = $(CURDIR)/codechecker_report_converter/report/output/html/static/vendor/codemirror

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

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

codemirror_dir:
	mkdir -p $ $(CODEMIRROR_DIR)

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
