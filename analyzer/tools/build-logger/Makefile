# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

CURRENT_DIR = ${CURDIR}
ROOT = $(CURRENT_DIR)

BUILD_DIR = $(CURRENT_DIR)/build
PYTHON_BIN ?= python3

ACTIVATE_DEV_VENV ?= . venv_dev/bin/activate

VENV_DEV_REQ_FILE ?= requirements_py/dev/requirements.txt

venv_dev:
	# Create a virtual environment for development.
	$(PYTHON_BIN) -m venv venv_dev && \
		$(ACTIVATE_DEV_VENV) && pip3 install -r $(VENV_DEV_REQ_FILE)

# import the test targets
include tests/Makefile


# build targets
# =============
# Input variables:
#  CC (default is gcc)
#
# Output:
#  ldlogger
#  ldlogger_32.so
#  ldlogger_64.so

# C compiler
CC ?= gcc
# Preprocessor flags
CPPFLAGS = -D_GNU_SOURCE
# C flags
CFLAGS = -std=c99 -pedantic -Wall -Wextra -O2
# Linker flags
LDFLAGS =
# Flags for ldlogger lib
LIB_CFLAGS= $(CFLAGS) \
	-Wno-strict-aliasing -fno-exceptions -fPIC -fomit-frame-pointer -fvisibility=hidden
# Linker flags for ldlogger lib
LIB_LDFLAGS= -shared -Wl,--no-as-needed -ldl

# Source files (keep it sync with Makefile.am)
LDLOGGER_HEADERS =  \
	src/ldlogger-hooks.h \
	src/ldlogger-tool.h \
	src/ldlogger-util.h

LDLOGGER_SOURCES = \
	src/ldlogger-logger.c \
	src/ldlogger-tool.c \
	src/ldlogger-tool-gcc.c \
	src/ldlogger-tool-javac.c \
	src/ldlogger-util.c

# Sorces for ldlogger
LDLOGGER_LIB_HEADERS = \
	src/ldlogger-hooks.h
LDLOGGER_LIB_SOURCES = \
	src/ldlogger-hooks.c

BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin
LIB_DIR = $(BUILD_DIR)/lib

# One rule to rule them all
all: ldlogger ldlogger_32.so ldlogger_64.so pack32bit pack64bit

pack32bit: 32bit packbin
	for x86dir in 'i386' 'i486' 'i586' 'i686'; do \
		mkdir -p $(LIB_DIR)/$$x86dir ; \
		cp ldlogger_32.so $(LIB_DIR)/$$x86dir/ldlogger.so ; \
	done
	rm -f ldlogger_32.so

pack64bit: 64bit packbin
	for x8664dir in 'x86_64'; do \
		mkdir -p $(LIB_DIR)/$$x8664dir ; \
		cp ldlogger_64.so $(LIB_DIR)/$$x8664dir/ldlogger.so ; \
	done
	rm -f ldlogger_64.so

pack64bit_only: 64bit_only packbin64
	for x8664dir in 'x86_64'; do \
		mkdir -p $(LIB_DIR)/$$x8664dir ; \
		cp ldlogger_64.so $(LIB_DIR)/$$x8664dir/ldlogger.so ; \
	done
	rm -f ldlogger_64.so

# pack binary
packbin:
	mkdir -p $(BIN_DIR)
	cp ldlogger $(BIN_DIR)
	rm -f ldlogger

# pack binary
packbin64:
	mkdir -p $(BIN_DIR)
	cp ldlogger64 $(BIN_DIR)/ldlogger
	rm -f ldlogger64

# Build only 32 bit lib
32bit: ldlogger ldlogger_32.so

# Build only 64 bit lib
64bit: ldlogger ldlogger_64.so

# Build only 64 bit lib and logger
64bit_only: ldlogger64 ldlogger_64.so

# Cleaner rule
clean:
	rm -rf $(BUILD_DIR)
	rm -f ldlogger ldlogger_32.so ldlogger_64.so

# ldlogger executable
ldlogger: $(LDLOGGER_SOURCES) $(LDLOGGER_HEADERS)
	$(CC) -m32 $(CPPFLAGS) $(CFLAGS) -D__LOGGER_MAIN__ $(LDFLAGS) $(LDLOGGER_SOURCES) -o $@

# ldlogger executable
ldlogger64: $(LDLOGGER_SOURCES) $(LDLOGGER_HEADERS)
	$(CC) -m64 $(CPPFLAGS) $(CFLAGS) -D__LOGGER_MAIN__ $(LDFLAGS) $(LDLOGGER_SOURCES) -o $@

# ldlogger lib 32
ldlogger_32.so: $(LDLOGGER_LIB_SOURCES) $(LDLOGGER_LIB_HEADERS)
	$(CC) -m32 $(CPPFLAGS) $(LIB_CFLAGS) $(LIB_LDFLAGS) $(LDLOGGER_LIB_SOURCES) $(LDLOGGER_SOURCES) -o $@

# ldlogger lib 64
ldlogger_64.so: $(LDLOGGER_LIB_SOURCES) $(LDLOGGER_LIB_HEADERS)
	$(CC) -m64 $(CPPFLAGS) $(LIB_CFLAGS) $(LIB_LDFLAGS) $(LDLOGGER_LIB_SOURCES) $(LDLOGGER_SOURCES) -o $@
