# Makefile to build and analyze the test files required
# for the store update tests.

build:
	$(CXX) -c double_suppress/double_suppress.cpp -o double_suppress/double_suppress.o

clean:
	rm -rf double_suppress/double_suppress.o

# Using relative path to the source files
# it is easier to prefix them with the temporary
# directory during test preparation.
analyze:
	clang --analyze double_suppress.cpp --analyzer-output plist-multi-file \
        -o double_suppress.plist
