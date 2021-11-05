-include Makefile.local

# Set it to NO if you would not like to build the UI code.
BUILD_UI_DIST ?= YES

CURRENT_DIR = ${CURDIR}
BUILD_DIR ?= $(CURRENT_DIR)/build
PYTHON_BIN ?= python3

CC_BUILD_DIR = $(BUILD_DIR)/CodeChecker
CC_BUILD_WEB_DIR = $(CC_BUILD_DIR)/www
CC_BUILD_PLUGIN_DIR = $(CC_BUILD_DIR)/plugin
CC_BUILD_BIN_DIR = $(CC_BUILD_DIR)/bin
CC_BUILD_LIB_DIR = $(CC_BUILD_DIR)/lib/python3
CC_BUILD_SCRIPTS_DIR = $(CC_BUILD_WEB_DIR)/scripts
CC_BUILD_API_DIR = $(CC_BUILD_SCRIPTS_DIR)/codechecker-api
CC_BUILD_WEB_PLUGINS_DIR = $(CC_BUILD_SCRIPTS_DIR)/plugins
CC_BUILD_GEN_DIR = $(CC_BUILD_LIB_DIR)/codechecker_api

CC_SERVER = $(CURRENT_DIR)/server/
CC_CLIENT = $(CURRENT_DIR)/client/

# Root of the repository.
ROOT = $(CURRENT_DIR)/..

CC_TOOLS = $(ROOT)/tools
CC_WEB = $(ROOT)/web

ACTIVATE_RUNTIME_VENV ?= . venv/bin/activate
ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_REQ_FILE ?= requirements.txt
VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

DIST_DIR = $(CC_SERVER)/vue-cli/dist
LATEST_COMMIT_FILE = $(DIST_DIR)/.build-commit

ifneq (, $(shell which git))
# Get the latest commit in which the vue-cli directory was changed.
LATEST_COMMIT = $(shell git log -n 1 --pretty=format:%H $(CC_SERVER)/vue-cli)

# Get the latest build command from the dist directory.
LATEST_BUILD_COMMIT = $(shell cat ${LATEST_COMMIT_FILE} 2>/dev/null)
endif

include tests/Makefile
include server/tests/Makefile
include client/tests/Makefile

pip_dev_deps:
	pip3 install -r $(VENV_DEV_REQ_FILE)

venv:
	# Create a virtual environment which can be used to run the build package.
	python3 -m venv venv --prompt="CodeChecker web venv" && \
		$(ACTIVATE_RUNTIME_VENV) && pip3 install -r $(VENV_REQ_FILE)

venv_dev:
	# Create a virtual environment for development.
	python3 -m venv venv_dev --prompt="CodeChecker web venv-dev" && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

clean_venv:
	rm -rf venv

clean_venv_dev:
	rm -rf venv_dev

build_dir:
	mkdir -p $(BUILD_DIR)

package_dir_structure:
	mkdir -p $(BUILD_DIR) && \
	mkdir -p $(CC_BUILD_BIN_DIR) && \
	mkdir -p $(CC_BUILD_LIB_DIR)

$(DIST_DIR):
ifeq ($(BUILD_UI_DIST),YES)
	cd $(CC_SERVER)/vue-cli && \
	npm install && \
	npm run-script build && \
	echo $(LATEST_COMMIT) > $(LATEST_COMMIT_FILE)
endif

build_report_converter:
	$(MAKE) -C $(CC_TOOLS)/report-converter build

package_report_converter: build_report_converter package_dir_structure
	cp -rp $(CC_TOOLS)/report-converter/build/report_converter/codechecker_report_converter $(CC_BUILD_LIB_DIR) && \
	chmod u+x $(CC_BUILD_LIB_DIR)/codechecker_report_converter/cli.py && \
	cd $(CC_BUILD_BIN_DIR) && \
	ln -sf ../lib/python3/codechecker_report_converter/cli.py report-converter

# This target should be used from the top level Makefile to build the package
# together with the analyzer part. This way we will not build tools
# multiple times.
package_web: check_codechecker_api_version check_dist package_dir_structure package_report_converter $(DIST_DIR)
ifeq ($(BUILD_UI_DIST),YES)
	mkdir -p $(CC_BUILD_WEB_DIR)
	cp -r $(DIST_DIR)/* $(CC_BUILD_WEB_DIR)
endif

package: package_dir_structure package_web
	# Copy libraries.
	cp -r $(ROOT)/codechecker_common $(CC_BUILD_LIB_DIR) && \
	cp -r $(CURRENT_DIR)/codechecker_web $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_SERVER)/codechecker_server $(CC_BUILD_LIB_DIR) && \
	cp -r $(CC_CLIENT)/codechecker_client $(CC_BUILD_LIB_DIR)

	# Copy config files and extend 'version.json' file with git information.
	cp -r $(ROOT)/config $(CC_BUILD_DIR) && \
	cp -r $(CURRENT_DIR)/config/* $(CC_BUILD_DIR)/config && \
	cp -r $(CC_SERVER)/config/* $(CC_BUILD_DIR)/config && \
	${PYTHON_BIN} $(ROOT)/scripts/build/extend_version_file.py -r $(ROOT) \
	  $(CC_BUILD_DIR)/config/web_version.json

	# Copy CodeChecker entry point sub-commands.
	${PYTHON_BIN} $(ROOT)/scripts/build/create_commands.py -b $(BUILD_DIR) \
	  --cmd-dir $(ROOT)/codechecker_common/cmd \
	    $(CC_WEB)/codechecker_web/cmd \
	    $(CC_SERVER)/codechecker_server/cmd \
	    $(CC_CLIENT)/codechecker_client/cmd \
	  --bin-file $(ROOT)/bin/CodeChecker

	# Copy license file.
	cp $(ROOT)/LICENSE.TXT $(CC_BUILD_DIR)

package_api:
	${PYTHON_BIN} -m pip install --no-deps -t ${CC_BUILD_LIB_DIR} \
		api/py/codechecker_api/dist/codechecker_api.tar.gz \
		api/py/codechecker_api_shared/dist/codechecker_api_shared.tar.gz

standalone_package: venv package
	cd $(CC_BUILD_BIN_DIR) && \
	mv CodeChecker _CodeChecker && \
	${PYTHON_BIN} $(ROOT)/scripts/build/wrap_binary_in_venv.py \
		-e $(CURRENT_DIR)/venv \
		-b _CodeChecker \
		-o CodeChecker

# This target will check that 'codecheck_api' and 'codechecker_api_shared'
# python packages are up to date. If not, it will update these packages and
# removes the dist directory to make sure the the UI part will be built again.
check_codechecker_api_version:
	if ! pip3 install -r ./requirements.txt 2>&1 | grep -q "Requirement already satisfied: codechecker_api"; then \
		if [ "$(BUILD_UI_DIST)" = "YES" ]; then \
		  cd server/vue-cli && npm install && rm -rf $(DIST_DIR); \
		fi; \
	fi

# This target will check if the 'dist' directory exists and the vue-cli folder
# is changed. In this case it will remove the dist directory so the UI will
# be built again.
check_dist:
	if [ "$(BUILD_UI_DIST)" = "YES" ] && [ -d $(DIST_DIR) ] && [ "$(LATEST_COMMIT)" != "$(LATEST_BUILD_COMMIT)" ]; then \
	  cd server/vue-cli && npm install && rm -rf $(DIST_DIR); \
	fi

clean_package:
	rm -rf $(BUILD_DIR)
	rm -rf gen-docs
	find . -name "*.pyc" -delete

clean:
	rm -rf $(CC_SERVER)/vue-cli/dist
	rm -rf $(CC_SERVER)/vue-cli/node_modules
