#include <iostream>

int main() {
  int x;
  int y;

  std::cin >> x;

  if (false || x) {
    return 42;
  }

  return x % 0;
}
