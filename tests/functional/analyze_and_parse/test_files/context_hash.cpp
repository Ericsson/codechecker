#include <cstring>

#define BUFLEN 42

void foo()
{
  int x;
  x = 1;
}

void bar(int x)
{
  x = 1;
}

void baz()
{
  int z;
  z = 1;

  // context independent hash!
  char buf[BUFLEN];
  std::memset(buf, 0, sizeof(BUFLEN));  // sizeof(42) ==> sizeof(int)
}

int main()
{
  foo();
  int x = 4;
  bar(x);
  baz();

  char buf[BUFLEN];
  std::memset(buf, 0, sizeof(BUFLEN));  // sizeof(42) ==> sizeof(int)

// Indentation independent hash!
std::memset(buf, 0, sizeof(BUFLEN));  // sizeof(42) ==> sizeof(int)

  return 0;
}
