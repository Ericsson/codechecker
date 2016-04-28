#include <iostream>

int foo(int y) {
  if (y <= 0) {
    return 0;
  }

  return 42;
}

int main() {
  int x, y;

  std::cin >> y;

  x = foo(y);

  return 2015 / x;
}
