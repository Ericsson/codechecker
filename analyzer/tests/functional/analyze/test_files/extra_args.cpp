#include <functional>

int add(int x, int y) { return x + y; }

int main()
{
  #ifdef TIDYARGS
  int i = 1 / 0;
  #endif

  #ifdef SAARGS
  int* p = 0;
  *p = 42;
  #endif

  int x = 2;
  auto clj = std::bind(add, x, std::placeholders::_1);

  bool b = 1;
}
