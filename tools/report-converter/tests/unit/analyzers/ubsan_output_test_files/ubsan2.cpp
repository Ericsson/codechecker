#include <limits.h>

// Load of a value of an enumerated type which is not in the range of
// representable values for that enumerated type.
int f()
{
  enum E {
    a = 1
  };

  int value = 7;
  enum E *e = (enum E *)&value;
  return *e;
}

// Load of a bool value which is neither true nor false.
bool g()
{
  int result = 2;
  bool *predicate = (bool *)&result;
  if (*predicate) { // Error: variable is not a valid Boolean
    return true;
  }
  return false;
}

int main()
{
  f();
  g();
}
