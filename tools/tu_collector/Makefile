# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate
ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

venv:
	# Create a virtual environment which can be used to run the build package.
	python3 -m venv venv && $(ACTIVATE_RUNTIME_VENV)

venv_dev:
	# Create a virtual environment for development.
	python3 -m venv venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv_dev:
	rm -rf venv_dev

include tests/Makefile
