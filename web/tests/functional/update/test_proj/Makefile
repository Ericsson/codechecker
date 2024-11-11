# Makefile to build and analyze the test files required
# for the store update tests.

build:
	$(CXX) main.cpp -o main

clean:
	rm -rf main

# Using relative path to the source files
# it is easier to prefix them with the temporary
# directory during test preparation.
analyze:
	clang --analyze main.cpp --analyzer-output plist-multi-file \
	-o reports/base/base.plist

analyze_disable:
	clang --analyze main.cpp -Xanalyzer \
	-analyzer-disable-checker -Xanalyzer deadcode.DeadStores \
	--analyzer-output plist-multi-file \
	-o reports/disabled/disabled.plist
