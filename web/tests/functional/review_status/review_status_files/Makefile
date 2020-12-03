# Makefile to build and analyze the test files required
# for the store update tests.

build:
	$(CXX) divide_zero.cpp -o divide_zero

clean:
	rm -rf divide_zero

# Using relative path to the source files
# it is easier to prefix them with the temporary
# directory during test preparation.
analyze:
	clang --analyze -I. divide_zero.cpp --analyzer-output plist-multi-file \
        -o divide_zero.plist
