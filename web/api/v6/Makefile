# Set this variable to '1' if you would like to build Thrift stubs by
# using docker.
BUILD_WITH_DOCKER ?= 0

# Thrift docker image version which is used to generate Thrift stubs.
DOCKER_THRIFT_VERSION ?= 0.11.0

CURRENT_DIR = $(shell pwd)
API_DIR = $(CURRENT_DIR)/..
GEN_API_DIR = $(CURRENT_DIR)/codechecker_api_$(VERSION)

TARGET_PY = --gen py
TARGET_JS = --gen js:jquery

default: api

ifeq ($(BUILD_WITH_DOCKER),1)
DOCKER_RUN_CMD = docker run \
  --rm \
  -v "$(GEN_API_DIR):/build" \
  -v "$(API_DIR):/api" \
  thrift:$(DOCKER_THRIFT_VERSION) \
  thrift -r -o /build -I /api $(TARGET_PY) $(TARGET_JS)

api:
	mkdir -p $(GEN_API_DIR)
	$(DOCKER_RUN_CMD) /api/$(VERSION)/authentication.thrift
	$(DOCKER_RUN_CMD) /api/$(VERSION)/products.thrift
	$(DOCKER_RUN_CMD) /api/$(VERSION)/report_server.thrift
	$(DOCKER_RUN_CMD) /api/$(VERSION)/configuration.thrift
else
RUN_CMD = thrift -r -o $(GEN_API_DIR) -I ../ $(TARGET_PY) $(TARGET_JS)

api:
	mkdir -p $(GEN_API_DIR)
	$(RUN_CMD) authentication.thrift
	$(RUN_CMD) products.thrift
	$(RUN_CMD) report_server.thrift
	$(RUN_CMD) configuration.thrift
endif
