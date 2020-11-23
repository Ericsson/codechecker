THRIFT_OPTS = -r -o /data
THRIFT_VERSION = "0.11.0"
TARGET_PY = --gen py
TARGET_JS = --gen js:jquery --gen js:node
PYTHON_BIN ?= python3

current_dir = ${CURDIR}
uid = $(shell id -u)
guid = $(shell id -g)

API_DIR := $(current_dir)

PY_API_DIR = "$(API_DIR)/py/codechecker_api/codechecker_api"
PY_API_SHARED_DIR = "$(API_DIR)/py/codechecker_api_shared/codechecker_api_shared"
JS_API_DIR = "$(API_DIR)/js/codechecker-api-js/lib"
NODE_JS_API_DIR = "$(API_DIR)/js/codechecker-api-node/lib"

default: build

install_shared_py:
	cd codechecker_api_shared && ${PYTHON_BIN} setup.py install

install_api_py:
	cd codechecker_api && ${PYTHON_BIN} setup.py install

install_py: install_shared_py install_api_py

target_dirs:
	mkdir -p $(PY_API_DIR)
	mkdir -p $(PY_API_SHARED_DIR)
	mkdir -p $(JS_API_DIR)
	mkdir -p $(NODE_JS_API_DIR)

build: clean target_dirs
	docker run \
	  -u "$(uid):$(guid)" \
	  -v $(API_DIR):/data \
	  thrift:$(THRIFT_VERSION) \
	  /bin/bash -c " \
		thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) /data/authentication.thrift && \
		thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) /data/products.thrift && \
		thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) /data/report_server.thrift && \
		thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) /data/configuration.thrift && \
		thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) /data/server_info.thrift"

	cp -r $(API_DIR)/gen-js/* $(JS_API_DIR)
	cp -r $(API_DIR)/gen-nodejs/* $(NODE_JS_API_DIR)

	cp -r $(API_DIR)/gen-py/codechecker_api_shared/* $(PY_API_SHARED_DIR)
	rm -rf $(API_DIR)/gen-py/codechecker_api_shared

	cp -r $(API_DIR)/gen-py/* $(PY_API_DIR)

	rm -rf $(API_DIR)/gen-js/
	rm -rf $(API_DIR)/gen-nodejs/
	rm -rf $(API_DIR)/gen-py/

publish: build publish_py publish_js

publish_py:
	cd py/codechecker_api && ${PYTHON_BIN} setup.py sdist bdist_wheel && twine upload dist/* --verbose
	cd py/codechecker_api_shared && ${PYTHON_BIN} setup.py sdist bdist_wheel && twine upload dist/* --verbose

publish_test_py:
	cd py/codechecker_api && ${PYTHON_BIN} setup.py sdist bdist_wheel && twine upload --repository-url https://test.pypi.org/legacy/ dist/* --verbose
	cd py/codechecker_api_shared && ${PYTHON_BIN} setup.py sdist bdist_wheel && twine upload --repository-url https://test.pypi.org/legacy/ dist/* --verbose

publish_js:
	cd js/codechecker-api-js && npm publish
	cd js/codechecker-api-node && npm publish

publish_js_dev:
	cd js/codechecker-api-js && npm publish --tag dev
	cd js/codechecker-api-node && npm publish --tag dev

clean:
	git clean -xdf
