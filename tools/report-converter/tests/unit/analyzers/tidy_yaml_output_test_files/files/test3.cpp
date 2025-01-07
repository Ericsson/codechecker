#include "test3.hh"
#include <vector>
#include <iostream>

int main(int argc, const char** /*argv*/) {
  int* x = nullptr; // Using nullptr instead of 0 for better clarity

  // Unused variable and uninitialized variable
  int y;
  int z = y + 10; // `y` is uninitialized

  // Unnecessary copy of a vector
  std::vector<int> numbers = {1, 2, 3, 4, 5};
  std::vector<int> numbers_copy = numbers; // This copy can be avoided

  if (foo(argc > 3)) {
    bar(x);
  }

  // Missing check before dereferencing pointer
  int* p = nullptr;
  *p = 10; // Dereferencing a null pointer

  // Redundant check and potential null dereference
  if (x != nullptr) {
    std::cout << *x << std::endl; // x is null but it's checked only after dereferencing in `bar`
  }

  return 0;
}
