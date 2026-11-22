# Regenerate the ../*.out files with: make -C files
# clazy-standalone prints absolute paths, so the test directory prefix is
# rewritten to a relative one to keep the expected output machine-independent.
QT_INC ?= /usr/include/x86_64-linux-gnu/qt5
CLAZY_CMD = clazy-standalone --checks=level2,qstring-allocations
COMPILE_ARGS = -- clang++ -std=c++17 -fPIC -DQT_CORE_LIB -Wall \
	-isystem $(QT_INC) -isystem $(QT_INC)/QtCore
RELATIVE_PATHS = sed "s|$$(pwd)/||g"

all: main compile_error missing_include werror

main compile_error missing_include:
	cd .. && $(CLAZY_CMD) files/$@.cpp $(COMPILE_ARGS) 2>&1 | \
		$(RELATIVE_PATHS) > $@.out

werror:
	cd .. && $(CLAZY_CMD) files/compile_error.cpp $(COMPILE_ARGS) \
		-Werror=unused-variable 2>&1 | $(RELATIVE_PATHS) > $@.out

.PHONY: all main compile_error missing_include werror
