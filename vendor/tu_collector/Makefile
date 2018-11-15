# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin

default: all

all: package

package:
	mkdir -p $(BIN_DIR)
	cp tu_collector/tu_collector.py $(BIN_DIR)/tu-collector

clean:
	rm -rf $(BUILD_DIR)
