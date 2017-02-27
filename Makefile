-include Makefile.local

CURRENT_DIR = $(shell pwd)
BUILD_DIR = $(CURRENT_DIR)/build

# Root of the repository.
ROOT = $(CURRENT_DIR)

default: package

# Test running related targets.
include tests/Makefile

gen-docs: build_dir
	doxygen ./Doxyfile.in && \
	cp -a ./gen-docs $(BUILD_DIR)/gen-docs

thrift: build_dir

	if [ ! -d "$(BUILD_DIR)/gen-py" ]; then rm -rf $(BUILD_DIR)/gen-py; fi
	if [ ! -d "$(BUILD_DIR)/gen-js" ]; then rm -rf $(BUILD_DIR)/gen-js; fi

	thrift -r -o $(BUILD_DIR) -I thrift_api/ \
		--gen py thrift_api/report_storage_server.thrift

	thrift -r -o $(BUILD_DIR) -I thrift_api/ \
		--gen py --gen js:jquery thrift_api/report_viewer_server.thrift

	thrift -r -o $(BUILD_DIR) -I thrift_api/ \
		--gen py thrift_api/authentication.thrift

package: build_dir gen-docs thrift
	if [ ! -d "$(BUILD_DIR)/CodeChecker" ]; then \
		./scripts/build_package.py -r $(ROOT) -o $(BUILD_DIR) -b $(BUILD_DIR); \
	fi

travis:
	# travis specific changes
	scripts/change_clang_version.py $(CURRENT_DIR)

build_dir:
	mkdir -p build

venv:
	# virtual environment to run the package
	virtualenv -p python2 venv && \
		. venv/bin/activate && pip install -r .ci/basic_python_requirements

clean_venv:
	rm -rf venv

venv_dev:
	# virtual environment for development
	virtualenv -p python2 venv_dev && \
		. venv_dev/bin/activate && pip install -r .ci/python_requirements && \
		pip install -r tests/requirements.txt

clean_venv_dev:
	rm -rf venv_dev

clean:
	rm -rf build
	rm -rf gen-docs

