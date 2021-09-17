# Makefile to build and analyze the test files required
# for the store update tests.

build:
	$(CXX) -c divide_zero.cpp -o divide_zero.o

clean:
	rm -rf divide_zero.o

# Using relative path to the source files
# it is easier to prefix them with the temporary
# directory during test preparation.
analyze:
	clang --analyze -I. divide_zero.cpp --analyzer-output plist-multi-file \
        -o divide_zero.plist
