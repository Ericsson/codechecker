# Check if certain environmental variables are set properly.
include ../Makefile.check

THRIFT_OPTS = -r -o $(BUILD_DIR)/thrift/$(VERSION) -I ../

TARGET_PY = --gen py
TARGET_JS = --gen js:jquery

default: api

api:
	mkdir -p $(BUILD_DIR)/thrift/$(VERSION)
	thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) authentication.thrift
	thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) products.thrift
	thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) report_server.thrift
	thrift $(THRIFT_OPTS) $(TARGET_PY) $(TARGET_JS) configuration.thrift
